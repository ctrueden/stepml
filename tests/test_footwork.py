"""
Tests for beat → seconds timing and the foot-placement simulation.
"""

import numpy as np
import pytest

from stepml.features import footwork
from stepml.features.feature_extractor import FeatureExtractor
from stepml.features.timing import TimingMap
from stepml.utils.data_structures import (
    ChartData,
    ChartType,
    DifficultyType,
    NoteData,
    TimingEvent,
)


def _chart(bpms, stops=()):
    return ChartData(
        filepath="x.sm",
        format=".sm",
        songpack="test",
        bpms=[TimingEvent(b, v) for b, v in bpms],
        stops=[TimingEvent(b, v) for b, v in stops],
    )


def _rows(cols, n_cols, spacing=0.25):
    """One single-arrow row per entry of cols, `spacing` beats apart."""
    rows = []
    for i, c in enumerate(cols):
        pattern = ["0"] * n_cols
        pattern[c] = "1"
        rows.append((i * spacing, "".join(pattern)))
    return rows


class TestTimingMap:
    def test_constant_bpm(self):
        timing = TimingMap(_chart([(0, 120)]))
        assert timing.seconds([0, 4, 8]) == pytest.approx([0, 2, 4])

    def test_bpm_change(self):
        timing = TimingMap(_chart([(0, 120), (4, 240)]))
        # 4 beats at 120 (2 s), then 4 beats at 240 (1 s).
        assert timing.seconds([4, 8]) == pytest.approx([2, 3])

    def test_stop_applies_after_its_beat(self):
        timing = TimingMap(_chart([(0, 60)], stops=[(2, 1.5)]))
        assert timing.seconds([2, 3]) == pytest.approx([2, 4.5])

    def test_nonpositive_bpm_takes_no_time(self):
        timing = TimingMap(_chart([(0, 60), (2, -60), (4, 60)]))
        assert timing.seconds([2, 4, 5]) == pytest.approx([2, 2, 3])


class TestFootwork:
    def _simulate(self, chart_type, cols, n_cols, spacing=0.25, bpm=150):
        rows = _rows(cols, n_cols, spacing)
        times = np.array([beat for beat, _ in rows]) * 60.0 / bpm
        return footwork.simulate(chart_type, rows, times)

    def test_single_alternates_without_crossing(self):
        # L U D R L U D R ... in 16ths: a plain uncrossed stream.
        path = self._simulate(ChartType.SINGLE, [0, 2, 1, 3] * 8, 4)
        assert not path.crossed.any()
        assert path.left[:, 0].max() <= 1.0
        assert path.right[:, 0].min() >= 1.0

    def test_fast_sweep_forces_crossover(self):
        # L D R U L D R U in 16ths at 150 BPM: with alternating feet the left
        # foot must reach R past the right foot on D — a crossover, which at
        # this speed beats double-stepping.
        path = self._simulate(ChartType.SINGLE, [0, 1, 3, 2] * 8, 4)
        assert path.crossed.any()

    def test_double_pad_switching_moves_body(self):
        # Alternate between left pad and right pad every two beats.
        left_pad = [0, 3] * 4
        right_pad = [4, 7] * 4
        cols = (left_pad + right_pad) * 4
        path = self._simulate(ChartType.DOUBLE, cols, 8, spacing=0.5)
        body = path.body_x
        assert body.max() - body.min() > 2.0

    def test_unsupported_layout(self):
        assert footwork.simulate(ChartType.COUPLE, _rows([0], 8), np.zeros(1)) is None


class TestWeightShiftFeatures:
    def _features(self, chart_type, cols, n_cols, spacing=0.5, bpm=150):
        chart = _chart([(0, bpm)])
        note_data = NoteData(
            chart_type=chart_type,
            difficulty=DifficultyType.HARD,
            rating=10,
            raw_notes="",
            total_notes=len(cols),
            tap_notes=len(cols),
            note_positions=_rows(cols, n_cols, spacing),
        )
        chart.charts.append(note_data)
        return FeatureExtractor().extract_features(chart, note_data)

    def test_double_pad_switching_beats_single(self):
        single = self._features(ChartType.SINGLE, [0, 3] * 32, 4)
        double = self._features(ChartType.DOUBLE, ([0, 3] * 4 + [4, 7] * 4) * 4, 8)
        assert single.pad_shifts_per_second == 0
        assert double.pad_shifts_per_second > 0
        assert double.body_speed_mean > 2 * single.body_speed_mean

    def test_fast_pad_switches_survive_body_lag(self):
        # Hop between pads every two 16ths at 180 BPM (one switch per 0.17 s):
        # too fast for the lagged weight centre to follow across, but each
        # hop still moves the feet a full pad.
        fast = self._features(
            ChartType.DOUBLE, [0, 3, 4, 7] * 32, 8, spacing=0.25, bpm=180
        )
        assert fast.pad_switches_per_second > 2 * fast.pad_shifts_per_second
        assert fast.pad_switches_peak >= fast.pad_switches_per_second

    def test_stream_threshold_is_tempo_aware(self):
        # 8th notes: a stream at 220 BPM (0.136 s apart), not at 100 (0.3 s).
        fast = self._features(ChartType.SINGLE, [0, 2, 1, 3] * 16, 4, bpm=220)
        slow = self._features(ChartType.SINGLE, [0, 2, 1, 3] * 16, 4, bpm=100)
        assert fast.max_run_seconds > 0
        assert slow.max_run_seconds == 0
