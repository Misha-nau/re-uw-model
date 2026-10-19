"""LP/GP equity waterfall (Phase 5).

Distributes the net equity cash flow (Years 0..N, from ``returns.underwrite``) between an
LP and a GP that co-invests ``gp_coinvest_pct`` of the equity.

Contributions (negative cash flow) are split pro rata. Distributions run through segments:

* Segment 0 - return of capital + preferred return: 100% pro rata until the LP has
  received its contributions compounded at ``pref_rate`` (an IRR hurdle).
* Segment k (k = 1..K, one per ``tiers`` entry): cash is split with a GP promote p_k:
  GP share = p_k + (1 - p_k) x g, LP share = (1 - p_k) x (1 - g), until the LP reaches the
  tier's ``up_to_irr`` hurdle. The last tier (``up_to_irr = None``) takes everything else.

Each hurdle h is tracked as an LP balance: B_h(t) = B_h(t-1) x (1 + h) + LP contribution(t)
- LP distribution(t), accrued annually. Cash needed to clear a segment = B_h / LP share.
There is no GP catch-up.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .finance import equity_multiple, irr
from .inputs import Waterfall


@dataclass
class Segment:
    label: str
    hurdle: float | None  # LP IRR hurdle that closes this segment; None = uncapped
    promote: float  # GP promote share of the segment's cash


@dataclass
class WaterfallResult:
    segments: list[Segment]
    total_cf: np.ndarray  # Years 0..N
    lp_cf: np.ndarray
    gp_cf: np.ndarray
    lp_by_segment: np.ndarray  # [segment, year] distributions
    gp_by_segment: np.ndarray
    gp_coinvest_pct: float

    @property
    def gp_promote(self) -> float:
        """GP distributions in excess of its pro-rata share of total distributions."""
        dist = np.clip(self.total_cf, 0, None).sum()
        gp_dist = self.gp_by_segment.sum()
        return float(gp_dist - self.gp_coinvest_pct * dist)

    def metrics(self) -> dict[str, float | None]:
        return {
            "lp_irr": irr(self.lp_cf),
            "lp_multiple": equity_multiple(self.lp_cf),
            "lp_profit": float(self.lp_cf.sum()),
            "gp_irr": irr(self.gp_cf),
            "gp_multiple": equity_multiple(self.gp_cf),
            "gp_profit": float(self.gp_cf.sum()),
            "gp_promote": self.gp_promote,
        }

    def table(self, start_year: int, scale: float = 1.0) -> pd.DataFrame:
        n = len(self.total_cf)
        cols = [f"Y{t} {start_year + t - 1}" for t in range(n)]
        contrib = np.clip(self.total_cf, None, 0)
        rows: list[tuple[str, np.ndarray]] = [
            ("Equity cash flow (net of fees)", self.total_cf),
            ("LP contributions", contrib * (1 - self.gp_coinvest_pct)),
            ("GP contributions", contrib * self.gp_coinvest_pct),
        ]
        for i, s in enumerate(self.segments):
            rows.append((f"LP: {s.label}", self.lp_by_segment[i]))
            rows.append((f"GP: {s.label}", self.gp_by_segment[i]))
        rows += [("LP net cash flow", self.lp_cf), ("GP net cash flow", self.gp_cf)]
        return pd.DataFrame({k: v / scale + 0.0 for k, v in rows}, index=cols).T


def build_segments(w: Waterfall) -> list[Segment]:
    segs = [Segment(f"Return of capital + {w.pref_rate:.1%} pref", w.pref_rate, 0.0)]
    prev = w.pref_rate
    for t in w.tiers:
        if t.up_to_irr is None:
            label = f"Above {prev:.1%} ({t.gp_promote:.0%} promote)"
        else:
            label = f"{prev:.1%} to {t.up_to_irr:.1%} ({t.gp_promote:.0%} promote)"
            prev = t.up_to_irr
        segs.append(Segment(label, t.up_to_irr, t.gp_promote))
    return segs


def run_waterfall(w: Waterfall, equity_cf: np.ndarray) -> WaterfallResult:
    cf = np.asarray(equity_cf, dtype=float)
    g = w.gp_coinvest_pct
    n = len(cf)

    if not w.enabled:  # straight pro-rata split
        segs = [Segment("Pro rata (waterfall off)", None, 0.0)]
        dist = np.clip(cf, 0, None)
        return WaterfallResult(segs, cf, cf * (1 - g), cf * g,
                               (dist * (1 - g))[None, :], (dist * g)[None, :], g)

    segs = build_segments(w)
    hurdles = [s.hurdle for s in segs]
    balances = {h: 0.0 for h in hurdles if h is not None}
    lp_seg = np.zeros((len(segs), n))
    gp_seg = np.zeros((len(segs), n))

    for t in range(n):
        if t > 0:
            for h in balances:
                balances[h] *= 1.0 + h
        if cf[t] < 0:
            lp_contrib = -cf[t] * (1 - g)
            for h in balances:
                balances[h] += lp_contrib
            continue
        cash = cf[t]
        for i, s in enumerate(segs):
            if cash <= 0:
                break
            lp_share = (1 - s.promote) * (1 - g)
            if s.hurdle is None:
                take = cash
            else:
                need = max(balances[s.hurdle], 0.0)
                take = min(cash, need / lp_share) if lp_share > 0 else cash
            lp_amt = take * lp_share
            lp_seg[i, t] += lp_amt
            gp_seg[i, t] += take - lp_amt
            for h in balances:
                balances[h] -= lp_amt
            cash -= take

    contrib = np.clip(cf, None, 0)
    lp_cf = contrib * (1 - g) + lp_seg.sum(axis=0)
    gp_cf = contrib * g + gp_seg.sum(axis=0)
    return WaterfallResult(segs, cf, lp_cf, gp_cf, lp_seg, gp_seg, g)
