"""Singapore stamp duty on acquisition.

Rates as at 2026-10. Check IRAS before relying on them for a live deal.

* Buyer's Stamp Duty (BSD), non-residential: tiers effective for contracts / options
  dated on or after 15 Feb 2023.
* Share transfer duty: 0.2% of the higher of price or net asset value of the shares.
  Additional Conveyance Duties apply to *residential* property-holding entities only, so
  they are not modelled for an office/retail asset.
"""

from __future__ import annotations

from .inputs import Acquisition

# (band size, rate); the last band is open-ended (size None).
BSD_NON_RESIDENTIAL_TIERS: tuple[tuple[float | None, float], ...] = (
    (180_000, 0.01),
    (180_000, 0.02),
    (640_000, 0.03),
    (500_000, 0.04),
    (None, 0.05),
)

SHARE_TRANSFER_DUTY_RATE = 0.002


def bsd_non_residential(price: float) -> float:
    """Buyer's Stamp Duty on a non-residential property, in currency units."""
    remaining = max(price, 0.0)
    duty = 0.0
    for band, rate in BSD_NON_RESIDENTIAL_TIERS:
        chunk = remaining if band is None else min(remaining, band)
        duty += chunk * rate
        remaining -= chunk
        if remaining <= 0:
            break
    return duty


def share_transfer_duty(value: float) -> float:
    """Stamp duty on a transfer of shares/units (value = higher of price or NAV)."""
    return max(value, 0.0) * SHARE_TRANSFER_DUTY_RATE


def acquisition_stamp_duty(acq: Acquisition) -> float:
    """Stamp duty payable at closing for the chosen deal structure.

    For a share deal the purchase price is used as the NAV proxy (the property's
    value dominates the holding vehicle's NAV; liabilities are ignored).
    """
    if acq.stamp_duty_override_pct is not None:
        return acq.purchase_price * acq.stamp_duty_override_pct
    if acq.deal_structure == "share":
        return share_transfer_duty(acq.purchase_price)
    return bsd_non_residential(acq.purchase_price)
