import copy
import json

import pytest
from pydantic import ValidationError

from re_uw.inputs import UnderwritingInputs
from re_uw.scenarios import SCENARIOS_DIR, load_scenario, save_scenario

SAMPLE_PATH = SCENARIOS_DIR / "sample_sg_cbd_office_retail.json"


@pytest.fixture
def sample_dict() -> dict:
    with open(SAMPLE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _validate(d: dict) -> UnderwritingInputs:
    return UnderwritingInputs.model_validate(d)


def test_sample_loads():
    inp = load_scenario(SAMPLE_PATH)
    assert inp.analysis.currency == "SGD"
    assert [c.use_type for c in inp.components] == ["office", "retail"]
    assert inp.total_nla_sqft == 320_000
    assert inp.price_psf == pytest.approx(890_000_000 / 320_000)
    assert inp.debt.all_in_rate() == pytest.approx(0.031)
    assert inp.components[0].leasing.avg_lease_term_years == 3.0
    assert inp.acquisition.deal_structure == "asset"
    assert inp.fees.asset_mgmt_fee_basis == "gav"


def test_round_trip(tmp_path, sample_dict):
    inp = _validate(sample_dict)
    out = save_scenario(inp, tmp_path / "x.json")
    assert load_scenario(out) == inp


def test_override_keys_parsed_as_int(sample_dict):
    d = copy.deepcopy(sample_dict)
    d["components"][0]["revenue"]["vacancy_overrides"] = {"1": 0.15, "2": 0.10}
    inp = _validate(d)
    assert inp.components[0].revenue.vacancy_overrides == {1: 0.15, 2: 0.10}


def test_unknown_field_rejected(sample_dict):
    d = copy.deepcopy(sample_dict)
    d["exit"]["exit_cap"] = 0.04  # typo of exit_cap_rate
    with pytest.raises(ValidationError):
        _validate(d)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["components"][0]["revenue"].update(vacancy=1.5),
        lambda d: d["components"][0].update(nla_sqft=0),
        lambda d: d["acquisition"].update(purchase_price=-1),
        lambda d: d["components"].append(copy.deepcopy(d["components"][0])),  # duplicate name
        lambda d: d["components"].clear(),
        lambda d: d["capex"].update(one_off={"9": 1_000_000}),  # beyond 5-yr hold
        lambda d: d["components"][0]["revenue"].update(vacancy_overrides={"7": 0.1}),  # > N+1
        lambda d: d["components"][0]["revenue"].update(rent_growth_overrides={"1": 0.05}),
        lambda d: d["property"].update(lease_years_remaining=None),
        lambda d: d["property"].update(lease_years_remaining=4),  # shorter than hold
        lambda d: d["components"][0]["leasing"].update(rent_free_months_per_year_new=13),
        lambda d: d["components"][0]["leasing"].update(avg_lease_term_years=0),
        lambda d: d["components"][1].update(turnover_rent_pct=-0.1),
        lambda d: d["acquisition"].update(deal_structure="jv"),
        lambda d: d["debt"].update(base_rate_overrides={"6": 0.02}),  # after hold
        lambda d: d["debt"].update(base_rate_overrides={"2": 0.5}),
        lambda d: d["fees"].update(asset_mgmt_fee_basis="nav"),
        lambda d: d["expenses"].update(av_to_gpr_ratio=1.2),
    ],
    ids=[
        "vacancy>100%", "zero NLA", "negative price", "duplicate component", "no components",
        "capex after hold", "override beyond horizon", "growth override year 1",
        "leasehold without term", "lease shorter than hold",
        "rent-free > 12 months", "zero lease term", "negative turnover rent",
        "unknown deal structure", "rate override after hold", "rate override 50%",
        "unknown fee basis", "AV ratio > 100%",
    ],
)
def test_invalid_inputs_rejected(sample_dict, mutate):
    d = copy.deepcopy(sample_dict)
    mutate(d)
    with pytest.raises(ValidationError):
        _validate(d)


@pytest.mark.parametrize(
    "tiers",
    [
        [{"up_to_irr": 0.10, "gp_promote": 0.2}],  # last tier capped
        [{"up_to_irr": 0.05, "gp_promote": 0.2}, {"up_to_irr": None, "gp_promote": 0.3}],  # < pref
        [{"up_to_irr": 0.12, "gp_promote": 0.2}, {"up_to_irr": 0.10, "gp_promote": 0.2},
         {"up_to_irr": None, "gp_promote": 0.3}],  # not ascending
        [{"up_to_irr": None, "gp_promote": 0.2}, {"up_to_irr": None, "gp_promote": 0.3}],
    ],
    ids=["last capped", "below pref", "not ascending", "two uncapped"],
)
def test_bad_waterfall_tiers(sample_dict, tiers):
    d = copy.deepcopy(sample_dict)
    d["waterfall"]["tiers"] = tiers
    with pytest.raises(ValidationError):
        _validate(d)


def test_freehold_needs_no_lease_term(sample_dict):
    d = copy.deepcopy(sample_dict)
    d["property"].update(tenure="freehold", lease_years_remaining=None)
    assert _validate(d).property.tenure == "freehold"


def test_base_rate_curve(sample_dict):
    d = copy.deepcopy(sample_dict)
    d["debt"]["base_rate_overrides"] = {"2": 0.025}
    debt = _validate(d).debt
    assert debt.all_in_rate(1) == pytest.approx(0.031)  # 2.0% + 1.1%
    assert debt.all_in_rate(2) == pytest.approx(0.036)  # 2.5% + 1.1%


def test_defaults_fill_optional_sections(sample_dict):
    d = copy.deepcopy(sample_dict)
    for key in ("fees", "capex", "expenses", "debt"):
        d.pop(key)
    for c in d["components"]:
        for key in ("leasing", "recoveries_psf_pm", "recoveries_growth", "turnover_rent_pct"):
            c.pop(key)
    inp = _validate(d)
    assert inp.fees.enabled and inp.components[0].leasing.renewal_probability == 0.65
