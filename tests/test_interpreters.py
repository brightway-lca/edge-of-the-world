import math
from unittest.mock import patch

import pytest

import bw_eotw  # noqa: F401 — ensures all interpreters are registered
from bw_eotw.interpreters.loss import _scale_loss_uncertainty
from bw_eotw.registry import resolve, validate_edge


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

BASE_EDGE = {"row": 10, "col": 20, "flip": False}


def edge(**kwargs):
    return {**BASE_EDGE, **kwargs}


# ---------------------------------------------------------------------------
# temporal
# ---------------------------------------------------------------------------


class TestTemporalInterpreter:
    TEMPORAL_VALUES = {2010: 0.3, 2020: 0.4, 2030: 0.6}

    def resolve(self, config, values=None, default_year=None):
        edge_data = edge(
            interpreter="temporal",
            temporal_values=values or self.TEMPORAL_VALUES,
        )
        if default_year is not None:
            edge_data["default_year"] = default_year
        return list(resolve(edge_data, config))

    # --- exact year match ---

    def test_exact_year_match(self):
        entries = self.resolve({"year": 2030})
        assert len(entries) == 1
        assert entries[0].amount == pytest.approx(0.6)

    def test_exact_year_2010(self):
        entries = self.resolve({"year": 2010})
        assert entries[0].amount == pytest.approx(0.3)

    # --- default_year fallback (per-edge, not global) ---

    def test_default_year_used_when_config_year_missing(self):
        entries = self.resolve({}, default_year=2020)
        assert entries[0].amount == pytest.approx(0.4)

    def test_default_year_used_when_config_year_not_in_values(self):
        entries = self.resolve({"year": 2025}, default_year=2020)
        assert entries[0].amount == pytest.approx(0.4)

    def test_config_year_takes_priority_over_default_year(self):
        entries = self.resolve({"year": 2030}, default_year=2010)
        assert entries[0].amount == pytest.approx(0.6)  # 2030, not 2010

    # --- raises without a usable year ---

    def test_no_year_in_config_and_no_default_year_raises(self):
        with pytest.raises(KeyError, match="no 'year' in config"):
            self.resolve({})

    def test_year_not_in_values_and_no_default_year_raises(self):
        with pytest.raises(KeyError, match="year=2025"):
            self.resolve({"year": 2025}, values={2010: 0.3, 2030: 0.6})

    def test_error_message_lists_available_years(self):
        with pytest.raises(KeyError, match="2010"):
            self.resolve({"year": 2025}, values={2010: 0.3, 2030: 0.6})

    # --- value types ---

    def test_plain_number_value(self):
        entries = self.resolve({"year": 2020}, values={2020: 1.5})
        e = entries[0]
        assert e.amount == pytest.approx(1.5)
        assert e.loc == pytest.approx(1.5)
        assert e.uncertainty_type == 0

    def test_uncertainty_dict_value(self):
        values = {2020: {"amount": 0.4, "uncertainty_type": 2, "scale": 0.05}}
        entries = self.resolve({"year": 2020}, values=values)
        e = entries[0]
        assert e.amount == pytest.approx(0.4)
        assert e.uncertainty_type == 2
        assert e.scale == pytest.approx(0.05)

    # --- edge fields propagated ---

    def test_row_and_col_taken_from_edge(self):
        entries = self.resolve({"year": 2020})
        assert entries[0].row == 10
        assert entries[0].col == 20

    def test_flip_taken_from_edge(self):
        entries = list(
            resolve(
                {**BASE_EDGE, "flip": True, "interpreter": "temporal",
                 "temporal_values": {2020: 1.0}, "default_year": 2020},
                {},
            )
        )
        assert entries[0].flip is True


# ---------------------------------------------------------------------------
# loss
# ---------------------------------------------------------------------------


class TestLossInterpreter:
    def resolve(self, amount, loss_factor, extra=None):
        return list(
            resolve(
                edge(
                    interpreter="loss",
                    amount=amount,
                    loss_factor=loss_factor,
                    **(extra or {}),
                ),
                {},
            )
        )

    def test_yields_exactly_two_entries(self):
        assert len(self.resolve(1.0, 0.1)) == 2

    def test_first_entry_is_main_amount(self):
        entries = self.resolve(1.0, 0.1)
        assert entries[0].amount == pytest.approx(1.0)

    def test_second_entry_is_loss_amount(self):
        entries = self.resolve(1.0, 0.1)
        assert entries[1].amount == pytest.approx(0.1)

    def test_amounts_sum_to_gross(self):
        entries = self.resolve(2.0, 0.05)
        total = entries[0].amount + entries[1].amount
        assert total == pytest.approx(2.0 * 1.05)

    def test_zero_loss_factor_gives_zero_loss(self):
        entries = self.resolve(1.0, 0.0)
        assert entries[1].amount == pytest.approx(0.0)

    def test_both_entries_share_row_and_col(self):
        entries = self.resolve(1.0, 0.1)
        assert entries[0].row == entries[1].row == 10
        assert entries[0].col == entries[1].col == 20

    def test_loss_factor_as_uncertainty_dict(self):
        entries = self.resolve(
            2.0, {"amount": 0.1, "uncertainty_type": 2, "scale": 0.02}
        )
        loss_entry = entries[1]
        assert loss_entry.amount == pytest.approx(0.2)       # 2.0 * 0.1
        assert loss_entry.scale == pytest.approx(0.04)       # 2.0 * 0.02
        assert loss_entry.uncertainty_type == 2

    def test_main_entry_uncertainty_unaffected_by_loss_factor(self):
        entries = self.resolve(
            1.0, {"amount": 0.05, "uncertainty_type": 2, "scale": 0.01}
        )
        main = entries[0]
        assert main.uncertainty_type == 0  # from edge_data, not loss_factor
        assert math.isnan(main.scale)

    def test_main_entry_inherits_edge_uncertainty(self):
        entries = list(
            resolve(
                edge(
                    interpreter="loss",
                    amount=1.0,
                    uncertainty_type=2,
                    scale=0.1,
                    loss_factor=0.05,
                ),
                {},
            )
        )
        assert entries[0].uncertainty_type == 2
        assert entries[0].scale == pytest.approx(0.1)

    def test_flip_propagates_to_both_entries(self):
        entries = list(
            resolve(
                {**BASE_EDGE, "flip": True, "interpreter": "loss",
                 "amount": 1.0, "loss_factor": 0.1},
                {},
            )
        )
        assert entries[0].flip is True
        assert entries[1].flip is True


# ---------------------------------------------------------------------------
# _scale_loss_uncertainty helper
# ---------------------------------------------------------------------------


class TestScaleLossUncertainty:
    def test_scales_amount(self):
        result = _scale_loss_uncertainty({"amount": 0.1}, 2.0)
        assert result["amount"] == pytest.approx(0.2)

    def test_sets_loc_to_scaled_amount_when_absent(self):
        result = _scale_loss_uncertainty({"amount": 0.1}, 2.0)
        assert result["loc"] == pytest.approx(0.2)

    def test_scales_explicit_loc(self):
        result = _scale_loss_uncertainty({"amount": 0.1, "loc": 0.1}, 2.0)
        assert result["loc"] == pytest.approx(0.2)

    def test_scales_scale_field(self):
        result = _scale_loss_uncertainty({"amount": 0.1, "scale": 0.02}, 2.0)
        assert result["scale"] == pytest.approx(0.04)

    def test_scales_minimum_and_maximum(self):
        result = _scale_loss_uncertainty(
            {"amount": 0.1, "minimum": 0.05, "maximum": 0.15}, 2.0
        )
        assert result["minimum"] == pytest.approx(0.10)
        assert result["maximum"] == pytest.approx(0.30)

    def test_does_not_scale_shape(self):
        result = _scale_loss_uncertainty({"amount": 0.1, "shape": 3.0}, 2.0)
        assert result["shape"] == pytest.approx(3.0)

    def test_does_not_mutate_input(self):
        original = {"amount": 0.1, "scale": 0.01}
        _scale_loss_uncertainty(original, 5.0)
        assert original["scale"] == pytest.approx(0.01)


# ---------------------------------------------------------------------------
# validate_edge / loss validator
# ---------------------------------------------------------------------------


class TestLossValidation:
    def validate(self, loss_factor):
        validate_edge({"interpreter": "loss", "loss_factor": loss_factor, "input": ("db", "x")})

    def test_zero_is_valid(self):
        self.validate(0.0)

    def test_one_is_valid(self):
        self.validate(1.0)

    def test_midpoint_is_valid(self):
        self.validate(0.5)

    def test_above_one_raises(self):
        with pytest.raises(ValueError, match="0 and 1"):
            self.validate(1.001)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="0 and 1"):
            self.validate(-0.1)

    def test_uncertainty_dict_amount_checked(self):
        self.validate({"amount": 0.5, "uncertainty_type": 2, "scale": 0.05})

    def test_uncertainty_dict_above_one_raises(self):
        with pytest.raises(ValueError, match="0 and 1"):
            self.validate({"amount": 1.5, "uncertainty_type": 2})

    def test_missing_loss_factor_raises(self):
        with pytest.raises(ValueError, match="loss_factor"):
            validate_edge({"interpreter": "loss", "input": ("db", "x")})

    def test_non_loss_edge_not_validated(self):
        # temporal ignores loss_factor; only the input field is checked
        validate_edge({"interpreter": "temporal", "loss_factor": 99.0, "input": ("db", "x")})

    def test_edge_without_interpreter_not_validated(self):
        validate_edge({"amount": 1.0, "loss_factor": 99.0})


# ---------------------------------------------------------------------------
# scenario
# ---------------------------------------------------------------------------


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
        with pytest.raises(KeyError, match="scenario"):
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
            validate_edge({"interpreter": "scenario", "input": ("db", "x")})

    def test_empty_scenario_values_raises(self):
        with pytest.raises(ValueError, match="scenario_values"):
            validate_edge({"interpreter": "scenario", "scenario_values": {}, "input": ("db", "x")})

    def test_valid_scenario_values_passes(self):
        validate_edge({"interpreter": "scenario", "scenario_values": {"baseline": 1.0}, "input": ("db", "x")})


# ---------------------------------------------------------------------------
# provider_mix
# ---------------------------------------------------------------------------

# Integer node IDs used in mix entries (stored directly, no key lookup needed)
MIX = [
    {"input": 10, "share": 0.40},
    {"input": 11, "share": 0.35},
    {"input": 12, "share": 0.25},
]

# Maps integer node IDs to their database names, used to mock _get_node_database
FAKE_NODE_DATABASES = {10: "grid", 11: "grid", 12: "grid", 99: "other_db"}


def _fake_get_node_database(node_id):
    if node_id in FAKE_NODE_DATABASES:
        return FAKE_NODE_DATABASES[node_id]
    raise ValueError(f"No node found with id {node_id}")


class TestProviderMixInterpreter:
    def resolve(self, mix=None, amount=2.0, extra=None):
        edge_data = {
            **BASE_EDGE,
            "interpreter": "provider_mix",
            "product_name": "electricity",
            "amount": amount,
            "mix": mix if mix is not None else MIX,
            **(extra or {}),
        }
        return list(resolve(edge_data, {}))

    def test_yields_one_entry_per_provider(self):
        assert len(self.resolve()) == 3

    def test_amounts_are_share_times_total(self):
        entries = self.resolve(amount=2.0)
        amounts = {e.row: e.amount for e in entries}
        assert amounts[10] == pytest.approx(2.0 * 0.40)
        assert amounts[11] == pytest.approx(2.0 * 0.35)
        assert amounts[12] == pytest.approx(2.0 * 0.25)

    def test_amounts_sum_to_total_amount(self):
        entries = self.resolve(amount=3.0)
        assert sum(e.amount for e in entries) == pytest.approx(3.0)

    def test_all_entries_share_col(self):
        entries = self.resolve()
        assert all(e.col == BASE_EDGE["col"] for e in entries)

    def test_rows_are_input_ids(self):
        entries = self.resolve()
        assert {e.row for e in entries} == {10, 11, 12}

    def test_flip_propagates_to_all_entries(self):
        entries = self.resolve(extra={"flip": True})
        assert all(e.flip is True for e in entries)

    def test_single_provider_with_full_share(self):
        mix = [{"input": 10, "share": 1.0}]
        entries = self.resolve(mix=mix, amount=5.0)
        assert len(entries) == 1
        assert entries[0].amount == pytest.approx(5.0)
        assert entries[0].row == 10

    def test_config_is_ignored(self):
        edge_data = {
            **BASE_EDGE,
            "interpreter": "provider_mix",
            "product_name": "electricity",
            "amount": 1.0,
            "mix": MIX,
        }
        entries_no_config = list(resolve(edge_data, {}))
        entries_with_config = list(resolve(edge_data, {"year": 2030, "scenario": "x"}))
        assert [e.amount for e in entries_no_config] == [e.amount for e in entries_with_config]


class TestProviderMixValidation:
    def valid_edge(self, **overrides):
        base = {
            "interpreter": "provider_mix",
            "product_name": "electricity",
            "input": ("grid", "electricity"),
            "mix": list(MIX),
        }
        base.update(overrides)
        return base

    # Tests that pass structural checks reach super().validate(), which calls
    # _get_node_database.  Those tests patch it; structural-failure tests don't need to.

    def test_valid_edge_passes(self):
        with patch("bw_eotw.registry._get_node_database", side_effect=_fake_get_node_database):
            validate_edge(self.valid_edge())

    def test_missing_product_name_raises(self):
        with pytest.raises(ValueError, match="product_name"):
            validate_edge(self.valid_edge(product_name=""))

    def test_absent_product_name_raises(self):
        edge = self.valid_edge()
        del edge["product_name"]
        with pytest.raises(ValueError, match="product_name"):
            validate_edge(edge)

    def test_empty_mix_raises(self):
        with pytest.raises(ValueError, match="mix"):
            validate_edge(self.valid_edge(mix=[]))

    def test_missing_mix_raises(self):
        edge = self.valid_edge()
        del edge["mix"]
        with pytest.raises(ValueError, match="mix"):
            validate_edge(edge)

    def test_provider_missing_input_raises(self):
        # First provider has no 'input'; structural check fires before DB check.
        bad_mix = [{"share": 0.5}, {"input": 10, "share": 0.5}]
        with pytest.raises(ValueError, match="input"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_provider_non_integer_input_raises(self):
        bad_mix = [{"input": ("grid", "wind"), "share": 1.0}]
        with pytest.raises(ValueError, match="integer"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_provider_missing_share_raises(self):
        bad_mix = [{"input": 10}, {"input": 11, "share": 1.0}]
        with pytest.raises(ValueError, match="share"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_share_above_one_raises(self):
        bad_mix = [{"input": 10, "share": 1.1}, {"input": 11, "share": 0.0}]
        with pytest.raises(ValueError, match="0 and 1"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_negative_share_raises(self):
        bad_mix = [{"input": 10, "share": -0.1}, {"input": 11, "share": 1.1}]
        with pytest.raises(ValueError, match="0 and 1"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_shares_not_summing_to_one_raises(self):
        bad_mix = [{"input": 10, "share": 0.4}, {"input": 11, "share": 0.4}]
        with pytest.raises(ValueError, match="sum to 1"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_floating_point_sum_is_accepted(self):
        # 0.1 + 0.2 + 0.7 has a floating-point representation error
        mix = [
            {"input": 10, "share": 0.1},
            {"input": 11, "share": 0.2},
            {"input": 12, "share": 0.7},
        ]
        with patch("bw_eotw.registry._get_node_database", side_effect=_fake_get_node_database):
            validate_edge(self.valid_edge(mix=mix))

    def test_single_provider_at_full_share_is_valid(self):
        mix = [{"input": 10, "share": 1.0}]
        with patch("bw_eotw.registry._get_node_database", side_effect=_fake_get_node_database):
            validate_edge(self.valid_edge(mix=mix))

    def test_provider_from_different_database_raises(self):
        # node 99 maps to "other_db" in FAKE_NODE_DATABASES
        bad_mix = [{"input": 99, "share": 0.6}, {"input": 10, "share": 0.4}]
        with patch("bw_eotw.registry._get_node_database", side_effect=_fake_get_node_database):
            with pytest.raises(ValueError, match="database"):
                validate_edge(self.valid_edge(mix=bad_mix))


# ---------------------------------------------------------------------------
# provider_mix — normalize
# ---------------------------------------------------------------------------


class TestProviderMixNormalize:
    from bw_eotw.registry import normalize_edge

    def test_integer_input_unchanged(self):
        edge = {"interpreter": "provider_mix", "mix": [{"input": 42, "share": 1.0}]}
        from bw_eotw.registry import normalize_edge
        normalize_edge(edge)
        assert edge["mix"][0]["input"] == 42

    def test_node_instance_converted_to_id(self):
        from unittest.mock import MagicMock
        from bw_eotw.registry import normalize_edge
        fake_node = MagicMock()
        fake_node.id = 99
        edge = {"interpreter": "provider_mix", "mix": [{"input": fake_node, "share": 1.0}]}
        normalize_edge(edge)
        assert edge["mix"][0]["input"] == 99

    def test_non_interpreter_edge_unchanged(self):
        from bw_eotw.registry import normalize_edge
        edge = {"mix": [{"input": "not_an_id", "share": 1.0}]}
        normalize_edge(edge)
        assert edge["mix"][0]["input"] == "not_an_id"


# ---------------------------------------------------------------------------
# temporal_scenario
# ---------------------------------------------------------------------------

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
            validate_edge({"interpreter": "temporal_scenario", "input": ("db", "x")})

    def test_empty_scenario_temporal_values_raises(self):
        with pytest.raises(ValueError, match="scenario_temporal_values"):
            validate_edge({"interpreter": "temporal_scenario", "scenario_temporal_values": {}, "input": ("db", "x")})

    def test_empty_scenario_raises(self):
        with pytest.raises(ValueError, match="baseline"):
            validate_edge({
                "interpreter": "temporal_scenario",
                "scenario_temporal_values": {"baseline": {}},
                "input": ("db", "x"),
            })

    def test_valid_without_default_year_passes(self):
        validate_edge({
            "interpreter": "temporal_scenario",
            "scenario_temporal_values": SCENARIO_TEMPORAL_VALUES,
            "input": ("db", "x"),
        })

    def test_valid_with_default_year_passes(self):
        validate_edge({
            "interpreter": "temporal_scenario",
            "scenario_temporal_values": SCENARIO_TEMPORAL_VALUES,
            "default_year": 2020,
            "input": ("db", "x"),
        })

    def test_default_year_missing_from_one_scenario_raises(self):
        values = {
            "baseline":   {2020: 1.0, 2030: 0.9},
            "optimistic": {2030: 0.7},            # 2020 absent
        }
        with pytest.raises(ValueError, match="default_year"):
            validate_edge({
                "interpreter": "temporal_scenario",
                "scenario_temporal_values": values,
                "default_year": 2020,
                "input": ("db", "x"),
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
            "input": ("db", "x"),
        })
