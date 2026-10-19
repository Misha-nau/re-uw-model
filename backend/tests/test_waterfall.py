"""Waterfall tests, worked by hand.

Example A (no GP co-invest): equity -100 at Y0, +150 at Y1. Pref 10%; tier 1 to 20% IRR
with 20% promote; above 20%, 30% promote.
  Segment 0: LP needs 100 x 1.10 = 110 -> LP 110.            Cash left 40
  Segment 1: LP 20% balance = 120 - 110 = 10; LP share 0.8 -> cash 12.5: LP 10, GP 2.5. Left 27.5
  Segment 2: LP share 0.7 -> LP 19.25, GP 8.25
  LP = 139.25 (IRR 39.25%), GP = 10.75 (all promote)
"""

import numpy as np
import pytest

from re_uw.inputs import Waterfall
from re_uw.returns import underwrite
from re_uw.scenarios import SCENARIOS_DIR, load_scenario
from re_uw.waterfall import run_waterfall

A = pytest.approx


def wf(g=0.0, pref=0.10, tiers=None, enabled=True):
    tiers = tiers or [{"up_to_irr": 0.20, "gp_promote": 0.20},
                      {"up_to_irr": None, "gp_promote": 0.30}]
    return Waterfall(enabled=enabled, gp_coinvest_pct=g, pref_rate=pref, tiers=tiers)


def test_example_a_no_coinvest():
    r = run_waterfall(wf(), np.array([-100.0, 150.0]))
    assert r.lp_by_segment[:, 1] == A([110, 10, 19.25])
    assert r.gp_by_segment[:, 1] == A([0, 2.5, 8.25])
    assert r.lp_cf == A([-100, 139.25])
    assert r.gp_cf == A([0, 10.75])
    m = r.metrics()
    assert m["lp_irr"] == A(0.3925)
    assert m["gp_promote"] == A(10.75)


def test_example_a_with_10pct_coinvest():
    # LP 90 / GP 10 in. Seg 0: LP balance 99, LP share 0.9 -> cash 110: LP 99, GP 11. Left 40.
    # Seg 1: LP balance 108 - 99 = 9; LP share 0.8 x 0.9 = 0.72 -> cash 12.5: LP 9, GP 3.5
    # Seg 2: LP share 0.7 x 0.9 = 0.63 on 27.5 -> LP 17.325, GP 10.175
    r = run_waterfall(wf(g=0.10), np.array([-100.0, 150.0]))
    assert r.lp_cf == A([-90, 125.325])
    assert r.gp_cf == A([-10, 24.675])
    m = r.metrics()
    assert m["lp_irr"] == A(0.3925)  # same LP IRR as example A
    assert m["gp_promote"] == A(24.675 - 0.10 * 150)  # 9.675 above pro rata


def test_exactly_pref_means_no_promote():
    r = run_waterfall(wf(), np.array([-100.0, 0.0, 121.0]))  # exactly 10% over 2 years
    assert r.lp_cf == A([-100, 0, 121])
    assert r.metrics()["gp_promote"] == A(0.0, abs=1e-9)


def test_interim_distributions_reduce_hurdle_balance():
    # -100, +10, +110: 10% IRR exactly -> all to LP, nothing promoted
    r = run_waterfall(wf(), np.array([-100.0, 10.0, 110.0]))
    assert r.gp_cf.sum() == A(0.0, abs=1e-9)
    assert r.metrics()["lp_irr"] == A(0.10)


def test_capital_call_mid_hold():
    # -100, -50 (call), +200: contributions both accrue at the hurdles
    r = run_waterfall(wf(g=0.1), np.array([-100.0, -50.0, 200.0]))
    assert r.lp_cf[:2] == A([-90, -45])
    assert r.lp_cf.sum() + r.gp_cf.sum() == A(50.0)  # all cash allocated


def test_disabled_is_pro_rata():
    r = run_waterfall(wf(g=0.2, enabled=False), np.array([-100.0, 150.0]))
    assert r.lp_cf == A([-80, 120]) and r.gp_cf == A([-20, 30])
    assert r.gp_promote == A(0.0)


def test_cash_conserved_and_lp_irr_bounded_on_sample():
    res = underwrite(load_scenario(SCENARIOS_DIR / "sample_sg_cbd_office_retail.json"))
    w = res.waterfall
    assert w.lp_cf + w.gp_cf == A(res.levered_net_cf)
    # deal below pref: LP IRR equals deal IRR, no promote
    assert res.metrics["lp_irr"] == A(res.metrics["levered_irr"], abs=1e-9)
    assert res.metrics["gp_promote"] == A(0.0, abs=1e-6)


def test_upside_sample_hits_promote():
    res = underwrite(load_scenario(SCENARIOS_DIR / "upside_sg_cbd_office_retail.json"))
    m = res.metrics
    assert 0.07 < m["levered_irr"] < 0.10  # between the pref and the tier-1 hurdle
    assert m["gp_promote"] > 0
    assert 0.07 < m["lp_irr"] < m["levered_irr"] < m["gp_irr"]
    w = res.waterfall
    assert w.lp_by_segment[1].sum() > 0 and w.lp_by_segment[2].sum() == 0  # tier 1 only
    assert res.waterfall.lp_cf + res.waterfall.gp_cf == A(res.levered_net_cf)
