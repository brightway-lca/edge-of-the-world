import pytest

from bw_eotw.registry import resolve, validate_edge

BASE_EDGE = {"row": 10, "col": 20, "flip": False}


def edge(**kwargs):
    return {**BASE_EDGE, **kwargs}


SCENARIO_VALUES = {
    "baseline": 1.0,
    "optimistic": 0.7,
    "pessimistic": 1.3,
}


class TestScenarioInterpreter:
    def resolve(self, config, values=None):
        return list(
            resolve(
                edge(interpreter="scenario", scenario_values=values or SCENARIO_VALUES),
                config,
            )
        )

    def test_exact_scenario_match(self):
        entries = self.resolve({"scenario": "optimistic"})
        assert len(entries) == 1
        assert entries[0].amount == pytest.approx(0.7)

    def test_all_scenarios_resolve(self):
        for name, expected in SCENARIO_VALUES.items():
            entries = self.resolve({"scenario": name})
            assert entries[0].amount == pytest.approx(expected)

    def test_missing_scenario_key_in_config_raises(self):
        with pytest.raises(ValueError, match="requires a config"):
            self.resolve({})

    def test_unknown_scenario_raises(self):
        with pytest.raises(KeyError, match="unknown"):
            self.resolve({"scenario": "unknown"})

    def test_error_lists_available_scenarios(self):
        with pytest.raises(KeyError, match="baseline"):
            self.resolve({"scenario": "missing"})

    def test_plain_number_value(self):
        entries = self.resolve({"scenario": "baseline"}, values={"baseline": 2.5})
        assert entries[0].amount == pytest.approx(2.5)
        assert entries[0].loc == pytest.approx(2.5)
        assert entries[0].uncertainty_type == 0

    def test_uncertainty_dict_value(self):
        values = {"baseline": {"amount": 1.0, "uncertainty_type": 2, "scale": 0.1}}
        entries = self.resolve({"scenario": "baseline"}, values=values)
        assert entries[0].uncertainty_type == 2
        assert entries[0].scale == pytest.approx(0.1)

    def test_row_and_col_taken_from_edge(self):
        entries = self.resolve({"scenario": "baseline"})
        assert entries[0].row == 10
        assert entries[0].col == 20

    def test_flip_taken_from_edge(self):
        entries = list(
            resolve(
                {**BASE_EDGE, "flip": True, "interpreter": "scenario",
                 "scenario_values": {"baseline": 1.0}},
                {"scenario": "baseline"},
            )
        )
        assert entries[0].flip is True


class TestScenarioValidation:
    def test_missing_scenario_values_raises(self):
        with pytest.raises(ValueError, match="scenario_values"):
            validate_edge({"interpreter": "scenario", "input": 1})

    def test_empty_scenario_values_raises(self):
        with pytest.raises(ValueError, match="scenario_values"):
            validate_edge({"interpreter": "scenario", "scenario_values": {}, "input": 1})

    def test_valid_scenario_values_passes(self):
        validate_edge({"interpreter": "scenario", "scenario_values": {"baseline": 1.0}, "input": 1})
