import pytest

from bw_eotw.registry import resolve, validate_edge

BASE_EDGE = {"row": 10, "col": 20, "flip": False}


def edge(**kwargs):
    return {**BASE_EDGE, **kwargs}


SCENARIO_TEMPORAL_VALUES = {
    "baseline":   {2020: 1.00, 2030: 0.85},
    "optimistic": {2020: 0.80, 2030: {"amount": 0.60, "uncertainty_type": 2, "scale": 0.05}},
}


class TestTemporalScenarioInterpreter:
    def resolve(self, config, all_values=None, default_year=None):
        edge_data = edge(
            interpreter="temporal_scenario",
            scenario_temporal_values=all_values or SCENARIO_TEMPORAL_VALUES,
        )
        if default_year is not None:
            edge_data["default_year"] = default_year
        return list(resolve(edge_data, config))

    # --- scenario selection ---

    def test_exact_scenario_and_year(self):
        entries = self.resolve({"scenario": "baseline", "year": 2020})
        assert len(entries) == 1
        assert entries[0].amount == pytest.approx(1.00)

    def test_all_scenarios_resolve(self):
        expected = {"baseline": 1.00, "optimistic": 0.80}
        for name, val in expected.items():
            entries = self.resolve({"scenario": name, "year": 2020})
            assert entries[0].amount == pytest.approx(val)

    def test_missing_scenario_key_in_config_raises(self):
        with pytest.raises(KeyError, match="scenario"):
            self.resolve({"year": 2020})

    def test_unknown_scenario_raises(self):
        with pytest.raises(KeyError, match="unknown"):
            self.resolve({"scenario": "unknown", "year": 2020})

    def test_error_lists_available_scenarios(self):
        with pytest.raises(KeyError, match="baseline"):
            self.resolve({"scenario": "missing", "year": 2020})

    # --- year selection within scenario ---

    def test_exact_year_within_scenario(self):
        entries = self.resolve({"scenario": "baseline", "year": 2030})
        assert entries[0].amount == pytest.approx(0.85)

    def test_default_year_used_when_config_year_missing(self):
        entries = self.resolve({"scenario": "baseline"}, default_year=2020)
        assert entries[0].amount == pytest.approx(1.00)

    def test_default_year_used_when_config_year_not_in_scenario(self):
        entries = self.resolve({"scenario": "baseline", "year": 2025}, default_year=2020)
        assert entries[0].amount == pytest.approx(1.00)

    def test_config_year_takes_priority_over_default_year(self):
        entries = self.resolve({"scenario": "baseline", "year": 2030}, default_year=2020)
        assert entries[0].amount == pytest.approx(0.85)  # 2030, not 2020

    def test_no_year_and_no_default_year_raises(self):
        with pytest.raises(KeyError, match="no 'year' in config"):
            self.resolve({"scenario": "baseline"})

    def test_year_not_in_scenario_and_no_default_year_raises(self):
        with pytest.raises(KeyError, match="year=2025"):
            self.resolve({"scenario": "baseline", "year": 2025})

    def test_error_lists_available_years(self):
        with pytest.raises(KeyError, match="2020"):
            self.resolve({"scenario": "baseline", "year": 2025})

    # --- value types ---

    def test_plain_number_value(self):
        entries = self.resolve({"scenario": "baseline", "year": 2020})
        e = entries[0]
        assert e.amount == pytest.approx(1.00)
        assert e.loc == pytest.approx(1.00)
        assert e.uncertainty_type == 0

    def test_uncertainty_dict_value(self):
        entries = self.resolve({"scenario": "optimistic", "year": 2030})
        e = entries[0]
        assert e.amount == pytest.approx(0.60)
        assert e.uncertainty_type == 2
        assert e.scale == pytest.approx(0.05)

    # --- edge fields propagated ---

    def test_row_and_col_taken_from_edge(self):
        entries = self.resolve({"scenario": "baseline", "year": 2020})
        assert entries[0].row == 10
        assert entries[0].col == 20

    def test_flip_taken_from_edge(self):
        entries = list(
            resolve(
                {**BASE_EDGE, "flip": True, "interpreter": "temporal_scenario",
                 "scenario_temporal_values": {"s": {2020: 1.0}}},
                {"scenario": "s", "year": 2020},
            )
        )
        assert entries[0].flip is True


class TestTemporalScenarioValidation:
    def test_missing_scenario_temporal_values_raises(self):
        with pytest.raises(ValueError, match="scenario_temporal_values"):
            validate_edge({"interpreter": "temporal_scenario", "input": 1})

    def test_empty_scenario_temporal_values_raises(self):
        with pytest.raises(ValueError, match="scenario_temporal_values"):
            validate_edge({"interpreter": "temporal_scenario", "scenario_temporal_values": {}, "input": 1})

    def test_empty_scenario_raises(self):
        with pytest.raises(ValueError, match="baseline"):
            validate_edge({
                "interpreter": "temporal_scenario",
                "scenario_temporal_values": {"baseline": {}},
                "input": 1,
            })

    def test_valid_without_default_year_passes(self):
        validate_edge({
            "interpreter": "temporal_scenario",
            "scenario_temporal_values": SCENARIO_TEMPORAL_VALUES,
            "input": 1,
        })

    def test_valid_with_default_year_passes(self):
        validate_edge({
            "interpreter": "temporal_scenario",
            "scenario_temporal_values": SCENARIO_TEMPORAL_VALUES,
            "default_year": 2020,
            "input": 1,
        })

    def test_default_year_missing_from_one_scenario_raises(self):
        values = {
            "baseline":   {2020: 1.0, 2030: 0.9},
            "optimistic": {2030: 0.7},
        }
        with pytest.raises(ValueError, match="default_year"):
            validate_edge({
                "interpreter": "temporal_scenario",
                "scenario_temporal_values": values,
                "default_year": 2020,
                "input": 1,
            })

    def test_default_year_present_in_all_scenarios_passes(self):
        values = {
            "baseline":   {2020: 1.0, 2030: 0.9},
            "optimistic": {2020: 0.8, 2030: 0.7},
        }
        validate_edge({
            "interpreter": "temporal_scenario",
            "scenario_temporal_values": values,
            "default_year": 2020,
            "input": 1,
        })
