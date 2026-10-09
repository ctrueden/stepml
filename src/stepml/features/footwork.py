"""
Foot-placement simulation: which foot hits each arrow, and where the body is.

A Viterbi pass over (left-foot panel, right-foot panel, last foot moved)
chooses the cheapest foot assignment for the whole chart, trading off foot
travel, crossovers, double-steps (same foot twice in a row, much worse at
speed), and overstretching. The resulting foot positions give the player's
weight centre after every step, which is what makes double physically hard:
on single you stay centred over four arrows, while on double you must keep
hauling your centre of gravity between pads.

Holds are not modelled, so a held foot may occasionally be simulated as
moving; stepping while holding is measured separately (see FeatureExtractor).
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from stepml.utils.data_structures import ChartType

# Panel (x, y) centres in panel units. Up/Down sit in the pad's centre column.
_SINGLE = [(0.0, 0.0), (1.0, -1.0), (1.0, 1.0), (2.0, 0.0)]  # L D U R
# Double pads are adjacent: left pad's R panel touches right pad's L panel.
_DOUBLE = _SINGLE + [(x + 3.0, y) for x, y in _SINGLE]
# Solo: L UL D U UR R.
_SOLO = [(0.0, 0.0), (0.0, 1.0), (1.0, -1.0), (1.0, 1.0), (2.0, 1.0), (2.0, 0.0)]

_LAYOUTS = {
    ChartType.SINGLE: (_SINGLE, (0, 3)),
    ChartType.DOUBLE: (_DOUBLE, (3, 4)),  # start centred: left-R, right-L
    ChartType.SOLO: (_SOLO, (0, 5)),
}

_BIG = 1e9

# Cost weights (panel units of "effort"). Tuned so the simulation crosses over
# rather than double-stepping in fast streams, but double-steps at slow tempo.
_CROSS_BASE = 1.0  # any crossed stance
_CROSS_PER_UNIT = 1.0  # plus this per panel of crossing
_STRETCH_FREE = 2.5  # feet this far apart (euclidean) cost nothing extra
_STRETCH_PER_UNIT = 2.0
_DOUBLESTEP_BASE = 0.5
_DOUBLESTEP_SPEED = 0.35  # × 1/dt (seconds)
_MIN_DT = 0.05


# The body's weight centre lags the feet: it settles toward their midpoint
# with this time constant. Rapid left-right stepping on one pad averages out
# to little net motion, while dwelling on a pad pulls the weight across to it.
_BODY_LAG = 0.4  # seconds


@dataclass
class FootworkPath:
    """Simulated stance after each step row."""

    times: np.ndarray  # seconds
    left: np.ndarray  # (n, 2) panel coordinates of the left foot
    right: np.ndarray  # (n, 2) panel coordinates of the right foot

    @property
    def mid_x(self) -> np.ndarray:
        """Lateral midpoint of the feet after each step (unfiltered)."""
        return (self.left[:, 0] + self.right[:, 0]) / 2.0

    @property
    def body_x(self) -> np.ndarray:
        """Lateral weight centre, low-pass filtered over time."""
        mid = self.mid_x
        alpha = 1.0 - np.exp(-np.diff(self.times, prepend=self.times[0]) / _BODY_LAG)
        body = np.empty_like(mid)
        body[0] = mid[0]
        for i in range(1, len(mid)):
            body[i] = body[i - 1] + alpha[i] * (mid[i] - body[i - 1])
        return body

    @property
    def foot_travel(self) -> np.ndarray:
        """Distance moved by the feet (panels) at each row."""
        moves = np.zeros(len(self.times))
        for foot in (self.left, self.right):
            moves[1:] += np.hypot(*np.diff(foot, axis=0).T)
        return moves

    @property
    def crossed(self) -> np.ndarray:
        return self.left[:, 0] > self.right[:, 0]


def panel_distances(chart_type: ChartType) -> Optional[np.ndarray]:
    """Distance (panel units) between every pair of panels, or None."""
    if chart_type not in _LAYOUTS:
        return None
    panels = np.array(_LAYOUTS[chart_type][0])
    return np.hypot(
        panels[:, None, 0] - panels[None, :, 0], panels[:, None, 1] - panels[None, :, 1]
    )


def _stance_penalty(panels: np.ndarray) -> np.ndarray:
    """Penalty for standing with left foot on panel i, right on panel j."""
    xs, ys = panels[:, 0], panels[:, 1]
    cross = xs[:, None] - xs[None, :]  # > 0 means left foot is right of right foot
    pen = np.where(cross > 0, _CROSS_BASE + _CROSS_PER_UNIT * cross, 0.0)
    spread = np.hypot(cross, ys[:, None] - ys[None, :])
    pen += np.maximum(spread - _STRETCH_FREE, 0.0) * _STRETCH_PER_UNIT
    np.fill_diagonal(pen, _BIG)  # both feet cannot share a panel
    return pen


def simulate(
    chart_type: ChartType, rows: Sequence[Tuple[float, str]], times: np.ndarray
) -> Optional[FootworkPath]:
    """
    Choose the cheapest foot assignment for the given step rows.

    Args:
        chart_type: Play style (couple and unknown layouts are not simulated)
        rows: (beat, pattern) for rows containing at least one step
        times: Seconds for each row

    Returns:
        FootworkPath, or None if the layout is unsupported or there are no rows
    """
    if chart_type not in _LAYOUTS or not rows:
        return None
    layout, (start_l, start_r) = _LAYOUTS[chart_type]
    panels = np.array(layout)
    n_panels = len(panels)
    dist = panel_distances(chart_type)
    stance = _stance_penalty(panels)

    # Per row: the panels stepped on, reduced to at most two (hands → extremes).
    steps: List[Tuple[int, ...]] = []
    for _, pattern in rows:
        cols = [i for i, c in enumerate(pattern[:n_panels]) if c in "124"]
        if len(cols) > 2:
            cols = sorted(cols, key=lambda i: panels[i, 0])
            cols = [cols[0], cols[-1]]
        steps.append(tuple(cols))

    # dp[i, j, k]: best cost with left on i, right on j, foot k moved last.
    dp = 0.5 * (dist[start_l][:, None] + dist[start_r][None, :]) + stance
    dp = np.repeat(dp[:, :, None], 2, axis=2)
    backptrs: List[Tuple[np.ndarray, ...]] = []
    prev_t = times[0] - 1.0

    idx = np.arange(n_panels)
    for cols, t in zip(steps, times):
        dt = max(t - prev_t, _MIN_DT)
        prev_t = t
        ds = _DOUBLESTEP_BASE + _DOUBLESTEP_SPEED / dt
        new = np.full_like(dp, _BIG)

        if len(cols) == 1:
            c = cols[0]
            # Double-step cost for each panel a foot might leave (0 = jack).
            leave = np.where(idx != c, ds, 0.0)
            # Left foot steps to c: min over previous left panel i and last
            # foot k (a double-step if k is also the left foot).
            m0 = dp[:, :, 0] + leave[:, None]
            m1 = dp[:, :, 1]
            cand = np.minimum(m0, m1) + dist[:, c][:, None]  # [i, j]
            best_i = cand.argmin(axis=0)
            bp_l = best_i * 2 + (m1[best_i, idx] < m0[best_i, idx])
            new[c, :, 0] = cand[best_i, idx] + stance[c, :]
            # Right foot steps to c: min over previous right panel j and k.
            m0 = dp[:, :, 0]
            m1 = dp[:, :, 1] + leave[None, :]
            cand = np.minimum(m0, m1) + dist[:, c][None, :]  # [i, j]
            best_j = cand.argmin(axis=1)
            bp_r = best_j * 2 + (m1[idx, best_j] < m0[idx, best_j])
            new[:, c, 1] = cand[idx, best_j] + stance[:, c]
            backptrs.append((bp_l, bp_r))
        else:
            a, b = cols
            best_k = dp.argmin(axis=2)
            m = np.take_along_axis(dp, best_k[:, :, None], axis=2)[:, :, 0]
            bps = []
            for lf, rf in ((a, b), (b, a)):
                cand = m + dist[:, lf][:, None] + dist[:, rf][None, :]
                i, j = divmod(int(cand.argmin()), n_panels)
                # Both feet just moved, so either may lead next: no double-step.
                new[lf, rf, :] = cand[i, j] + stance[lf, rf]
                bps.append((i, j, best_k[i, j]))
            backptrs.append(tuple(bps))
        dp = new

    # Backtrack from the cheapest final stance.
    i, j, k = np.unravel_index(int(dp.argmin()), dp.shape)
    lefts = np.empty(len(steps), dtype=int)
    rights = np.empty(len(steps), dtype=int)
    for r in range(len(steps) - 1, -1, -1):
        lefts[r], rights[r] = i, j
        cols, bp = steps[r], backptrs[r]
        if len(cols) == 1:
            if k == 0:
                i, k = divmod(int(bp[0][j]), 2)
            else:
                j, k = divmod(int(bp[1][i]), 2)
        else:
            orient = 0 if (i, j) == (cols[0], cols[1]) else 1
            i, j, k = bp[orient]

    return FootworkPath(
        times=np.asarray(times, dtype=float),
        left=panels[lefts],
        right=panels[rights],
    )
