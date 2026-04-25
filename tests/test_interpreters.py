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

    def resolve(self, config, values=None):
        return list(
            resolve(
                edge(
                    interpreter="temporal",
                    temporal_values=values or self.TEMPORAL_VALUES,
                ),
                config,
            )
        )

    def test_exact_year_match(self):
        entries = self.resolve({"year": 2030})
        assert len(entries) == 1
        assert entries[0].amount == pytest.approx(0.6)

    def test_exact_year_2010(self):
        entries = self.resolve({"year": 2010})
        assert entries[0].amount == pytest.approx(0.3)

    def test_fallback_when_year_not_present(self):
        entries = self.resolve({"year": 2025})
        assert entries[0].amount == pytest.approx(0.4)  # 2020 fallback

    def test_empty_config_uses_default_year(self):
        entries = self.resolve({})
        assert entries[0].amount == pytest.approx(0.4)  # 2020 fallback

    def test_missing_year_and_missing_fallback_raises(self):
        with pytest.raises(KeyError, match="2020"):
            self.resolve({"year": 2025}, values={2010: 0.3, 2030: 0.6})

    def test_error_message_lists_available_years(self):
        with pytest.raises(KeyError, match="2010"):
            self.resolve({"year": 2025}, values={2010: 0.3, 2030: 0.6})

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

    def test_row_and_col_taken_from_edge(self):
        entries = self.resolve({"year": 2020})
        assert entries[0].row == 10
        assert entries[0].col == 20

    def test_flip_taken_from_edge(self):
        entries = list(
            resolve(
                {**BASE_EDGE, "flip": True, "interpreter": "temporal",
                 "temporal_values": {2020: 1.0}},
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
        validate_edge({"interpreter": "loss", "loss_factor": loss_factor})

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
            validate_edge({"interpreter": "loss"})

    def test_non_loss_edge_not_validated(self):
        validate_edge({"interpreter": "temporal", "loss_factor": 99.0})

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
            validate_edge({"interpreter": "scenario"})

    def test_empty_scenario_values_raises(self):
        with pytest.raises(ValueError, match="scenario_values"):
            validate_edge({"interpreter": "scenario", "scenario_values": {}})

    def test_valid_scenario_values_passes(self):
        validate_edge({"interpreter": "scenario", "scenario_values": {"baseline": 1.0}})


# ---------------------------------------------------------------------------
# provider_mix
# ---------------------------------------------------------------------------

MIX = [
    {"input": ("grid", "wind"),  "share": 0.40},
    {"input": ("grid", "solar"), "share": 0.35},
    {"input": ("grid", "gas"),   "share": 0.25},
]
# Stable fake IDs returned by the mocked get_id
FAKE_IDS = {("grid", "wind"): 10, ("grid", "solar"): 11, ("grid", "gas"): 12}


def _fake_get_id(key):
    return FAKE_IDS[key]


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
        with patch("bw_eotw.interpreters.provider_mix.get_id", side_effect=_fake_get_id):
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

    def test_rows_come_from_get_id(self):
        entries = self.resolve()
        assert {e.row for e in entries} == {10, 11, 12}

    def test_flip_propagates_to_all_entries(self):
        entries = self.resolve(extra={"flip": True})
        assert all(e.flip is True for e in entries)

    def test_single_provider_with_full_share(self):
        mix = [{"input": ("grid", "wind"), "share": 1.0}]
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
        with patch("bw_eotw.interpreters.provider_mix.get_id", side_effect=_fake_get_id):
            entries_no_config = list(resolve(edge_data, {}))
            entries_with_config = list(resolve(edge_data, {"year": 2030, "scenario": "x"}))
        assert [e.amount for e in entries_no_config] == [e.amount for e in entries_with_config]


class TestProviderMixValidation:
    def valid_edge(self, **overrides):
        base = {
            "interpreter": "provider_mix",
            "product_name": "electricity",
            "mix": list(MIX),
        }
        base.update(overrides)
        return base

    def test_valid_edge_passes(self):
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
        bad_mix = [{"share": 0.5}, {"input": ("db", "x"), "share": 0.5}]
        with pytest.raises(ValueError, match="input"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_provider_missing_share_raises(self):
        bad_mix = [{"input": ("db", "x")}, {"input": ("db", "y"), "share": 1.0}]
        with pytest.raises(ValueError, match="share"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_share_above_one_raises(self):
        bad_mix = [{"input": ("db", "x"), "share": 1.1}, {"input": ("db", "y"), "share": 0.0}]
        with pytest.raises(ValueError, match="0 and 1"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_negative_share_raises(self):
        bad_mix = [{"input": ("db", "x"), "share": -0.1}, {"input": ("db", "y"), "share": 1.1}]
        with pytest.raises(ValueError, match="0 and 1"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_shares_not_summing_to_one_raises(self):
        bad_mix = [{"input": ("db", "x"), "share": 0.4}, {"input": ("db", "y"), "share": 0.4}]
        with pytest.raises(ValueError, match="sum to 1"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_floating_point_sum_is_accepted(self):
        # 0.1 + 0.2 + 0.7 has a floating-point representation error
        mix = [
            {"input": ("db", "a"), "share": 0.1},
            {"input": ("db", "b"), "share": 0.2},
            {"input": ("db", "c"), "share": 0.7},
        ]
        validate_edge(self.valid_edge(mix=mix))

    def test_single_provider_at_full_share_is_valid(self):
        mix = [{"input": ("db", "only"), "share": 1.0}]
        validate_edge(self.valid_edge(mix=mix))
