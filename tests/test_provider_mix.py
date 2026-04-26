from unittest.mock import patch

import pytest

from bw_eotw.registry import resolve, validate_edge

BASE_EDGE = {"row": 10, "col": 20, "flip": False}


def edge(**kwargs):
    return {**BASE_EDGE, **kwargs}


MIX = [
    {"input": 10, "share": 0.40},
    {"input": 11, "share": 0.35},
    {"input": 12, "share": 0.25},
]

FAKE_NODE_DATABASES = {10: "grid", 11: "grid", 12: "grid", 50: "grid", 99: "other_db"}


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
            "input": 50,
            "mix": list(MIX),
        }
        base.update(overrides)
        return base

    def test_valid_edge_passes(self):
        with patch("bw_eotw.interpreters.provider_mix._get_node_database", side_effect=_fake_get_node_database):
            validate_edge(self.valid_edge())

    def test_missing_product_name_raises(self):
        with pytest.raises(ValueError, match="product_name"):
            validate_edge(self.valid_edge(product_name=""))

    def test_absent_product_name_raises(self):
        e = self.valid_edge()
        del e["product_name"]
        with pytest.raises(ValueError, match="product_name"):
            validate_edge(e)

    def test_empty_mix_raises(self):
        with pytest.raises(ValueError, match="mix"):
            validate_edge(self.valid_edge(mix=[]))

    def test_missing_mix_raises(self):
        e = self.valid_edge()
        del e["mix"]
        with pytest.raises(ValueError, match="mix"):
            validate_edge(e)

    def test_provider_missing_input_raises(self):
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

    def test_share_as_uncertainty_dict_raises(self):
        bad_mix = [{"input": 10, "share": {"amount": 0.5, "uncertainty_type": 2}}]
        with pytest.raises(ValueError, match="plain number"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_shares_not_summing_to_one_raises(self):
        bad_mix = [{"input": 10, "share": 0.4}, {"input": 11, "share": 0.4}]
        with pytest.raises(ValueError, match="sum to 1"):
            validate_edge(self.valid_edge(mix=bad_mix))

    def test_floating_point_sum_is_accepted(self):
        mix = [
            {"input": 10, "share": 0.1},
            {"input": 11, "share": 0.2},
            {"input": 12, "share": 0.7},
        ]
        with patch("bw_eotw.interpreters.provider_mix._get_node_database", side_effect=_fake_get_node_database):
            validate_edge(self.valid_edge(mix=mix))

    def test_single_provider_at_full_share_is_valid(self):
        mix = [{"input": 10, "share": 1.0}]
        with patch("bw_eotw.interpreters.provider_mix._get_node_database", side_effect=_fake_get_node_database):
            validate_edge(self.valid_edge(mix=mix))

    def test_provider_from_different_database_raises(self):
        bad_mix = [{"input": 99, "share": 0.6}, {"input": 10, "share": 0.4}]
        with patch("bw_eotw.interpreters.provider_mix._get_node_database", side_effect=_fake_get_node_database):
            with pytest.raises(ValueError, match="database"):
                validate_edge(self.valid_edge(mix=bad_mix))


class TestProviderMixNormalize:
    def test_integer_input_unchanged(self):
        from bw_eotw.registry import normalize_edge
        e = {"interpreter": "provider_mix", "mix": [{"input": 42, "share": 1.0}]}
        normalize_edge(e)
        assert e["mix"][0]["input"] == 42

    def test_node_instance_converted_to_id(self):
        from unittest.mock import MagicMock
        from bw_eotw.registry import normalize_edge
        fake_node = MagicMock()
        fake_node.id = 99
        e = {"interpreter": "provider_mix", "mix": [{"input": fake_node, "share": 1.0}]}
        normalize_edge(e)
        assert e["mix"][0]["input"] == 99

    def test_non_interpreter_edge_unchanged(self):
        from bw_eotw.registry import normalize_edge
        e = {"mix": [{"input": "not_an_id", "share": 1.0}]}
        normalize_edge(e)
        assert e["mix"][0]["input"] == "not_an_id"
