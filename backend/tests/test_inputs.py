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
    assert inp.debt.all_in_rate == pytest.approx(0.031)


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
    ],
    ids=[
        "vacancy>100%", "zero NLA", "negative price", "duplicate component", "no components",
        "capex after hold", "override beyond horizon", "growth override year 1",
        "leasehold without term", "lease shorter than hold",
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
