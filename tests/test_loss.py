import math

import pytest

from bw_eotw.registry import resolve, validate_edge

BASE_EDGE = {"row": 10, "col": 20, "flip": False}


def edge(**kwargs):
    return {**BASE_EDGE, **kwargs}


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

    def test_both_entries_have_no_uncertainty(self):
        entries = self.resolve(1.0, 0.1)
        for e in entries:
            assert e.uncertainty_type == 0
            assert math.isnan(e.scale)

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


class TestLossValidation:
    def validate(self, loss_factor):
        validate_edge({"interpreter": "loss", "loss_factor": loss_factor, "input": 1})

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

    def test_uncertainty_dict_raises(self):
        with pytest.raises(ValueError, match="plain number"):
            self.validate({"amount": 0.5, "uncertainty_type": 2, "scale": 0.05})

    def test_uncertainty_on_amount_raises(self):
        with pytest.raises(ValueError, match="uncertainty"):
            validate_edge({
                "interpreter": "loss",
                "amount": 1.0,
                "uncertainty_type": 2,
                "loss_factor": 0.05,
                "input": 1,
            })

    def test_missing_loss_factor_raises(self):
        with pytest.raises(ValueError, match="loss_factor"):
            validate_edge({"interpreter": "loss", "input": 1})

    def test_non_loss_edge_not_validated(self):
        validate_edge({"interpreter": "temporal", "loss_factor": 99.0, "input": 1})

    def test_edge_without_interpreter_not_validated(self):
        validate_edge({"amount": 1.0, "loss_factor": 99.0})
