"""
Beat → seconds conversion honoring BPM changes, stops, and delays.
"""

import numpy as np

from stepml.utils.data_structures import ChartData


class TimingMap:
    """Map beat positions to elapsed seconds for one chart."""

    def __init__(self, chart_data: ChartData):
        bpms = sorted(chart_data.bpms, key=lambda e: e.beat)
        if not bpms:
            bpms_beats, bpms_values = [0.0], [0.0]
        else:
            bpms_beats = [e.beat for e in bpms]
            bpms_values = [e.value for e in bpms]
            if bpms_beats[0] > 0:
                bpms_beats.insert(0, 0.0)
                bpms_values.insert(0, bpms_values[0])

        self._seg_beats = np.array(bpms_beats, dtype=float)
        # Note: non-positive BPMs are ITG-style gimmicks that skip over notes;
        # treating those segments as taking no time approximates a warp.
        values = np.array(bpms_values, dtype=float)
        self._seg_spb = np.where(values > 0, 60.0 / np.where(values > 0, values, 1), 0)
        seg_lengths = np.diff(self._seg_beats) * self._seg_spb[:-1]
        self._seg_secs = np.concatenate([[0.0], np.cumsum(seg_lengths)])

        # A stop pauses *after* notes on its beat; a delay pauses *before* them.
        self._stop_beats, self._stop_cum = self._pauses(chart_data.stops)
        self._delay_beats, self._delay_cum = self._pauses(chart_data.delays)

    @staticmethod
    def _pauses(events):
        events = sorted((e for e in events if e.value > 0), key=lambda e: e.beat)
        beats = np.array([e.beat for e in events], dtype=float)
        cum = np.concatenate([[0.0], np.cumsum([e.value for e in events])])
        return beats, cum

    @property
    def valid(self) -> bool:
        return bool(np.any(self._seg_spb > 0))

    def seconds(self, beats) -> np.ndarray:
        """Elapsed seconds at each beat (array-like in, array out)."""
        beats = np.asarray(beats, dtype=float)
        idx = np.clip(
            np.searchsorted(self._seg_beats, beats, side="right") - 1,
            0,
            len(self._seg_beats) - 1,
        )
        t = self._seg_secs[idx] + (beats - self._seg_beats[idx]) * self._seg_spb[idx]
        t += self._stop_cum[np.searchsorted(self._stop_beats, beats, side="left")]
        t += self._delay_cum[np.searchsorted(self._delay_beats, beats, side="right")]
        return t
