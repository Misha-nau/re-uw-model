import pytest

from re_uw.inputs import Acquisition
from re_uw.sg_tax import acquisition_stamp_duty, bsd_non_residential, share_transfer_duty


@pytest.mark.parametrize(
    "price, expected",
    [
        (0, 0),
        (100_000, 1_000),  # 1% of 100k
        (180_000, 1_800),
        (360_000, 1_800 + 3_600),
        (1_000_000, 1_800 + 3_600 + 19_200),
        (1_500_000, 1_800 + 3_600 + 19_200 + 20_000),  # 44,600
        (2_000_000, 44_600 + 25_000),  # + 5% of 500k
        # 890m: 5% x 890m - 30,400 (5% would be 75,000 on the first 1.5m, tiers give 44,600)
        (890_000_000, 890_000_000 * 0.05 - 30_400),
    ],
)
def test_bsd_tiers(price, expected):
    assert bsd_non_residential(price) == pytest.approx(expected, rel=1e-12)


def test_bsd_effective_rate_converges_to_5pct():
    assert bsd_non_residential(890_000_000) / 890_000_000 == pytest.approx(0.04997, abs=1e-5)


def test_share_duty():
    assert share_transfer_duty(890_000_000) == pytest.approx(1_780_000)


def _acq(**kw):
    return Acquisition(purchase_price=890_000_000, **kw)


def test_acquisition_stamp_duty_by_structure():
    assert acquisition_stamp_duty(_acq()) == pytest.approx(44_469_600)
    assert acquisition_stamp_duty(_acq(deal_structure="share")) == pytest.approx(1_780_000)
    assert acquisition_stamp_duty(
        _acq(deal_structure="share", stamp_duty_override_pct=0.03)
    ) == pytest.approx(26_700_000)
