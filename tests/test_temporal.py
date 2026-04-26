import pytest

from bw_eotw.registry import normalize_edge, resolve

BASE_EDGE = {"row": 10, "col": 20, "flip": False}


def edge(**kwargs):
    return {**BASE_EDGE, **kwargs}


TEMPORAL_VALUES = {2010: 0.3, 2020: 0.4, 2030: 0.6}


class TestTemporalInterpreter:
    def resolve(self, config, values=None, default_year=None):
        edge_data = edge(
            interpreter="temporal",
            temporal_values=values or TEMPORAL_VALUES,
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


class TestTemporalNormalize:
    def normalize(self, **kwargs):
        edge_data = {"interpreter": "temporal", **kwargs}
        normalize_edge(edge_data)
        return edge_data

    def test_amount_inferred_as_mean_of_plain_values(self):
        d = self.normalize(temporal_values={2020: 0.4, 2030: 0.6})
        assert d["amount"] == pytest.approx(0.5)

    def test_amount_inferred_from_default_year(self):
        d = self.normalize(temporal_values={2020: 0.5, 2030: 0.8}, default_year=2020)
        assert d["amount"] == pytest.approx(0.5)

    def test_default_year_takes_priority_over_mean(self):
        d = self.normalize(temporal_values={2020: 0.2, 2030: 0.8}, default_year=2020)
        assert d["amount"] == pytest.approx(0.2)

    def test_amount_inferred_from_uncertainty_dict_via_default_year(self):
        d = self.normalize(
            temporal_values={2020: {"amount": 0.4, "uncertainty_type": 2}},
            default_year=2020,
        )
        assert d["amount"] == pytest.approx(0.4)

    def test_explicit_amount_not_overwritten(self):
        d = self.normalize(temporal_values={2020: 0.5}, amount=2.0)
        assert d["amount"] == pytest.approx(2.0)

    def test_empty_temporal_values_leaves_amount_absent(self):
        d = self.normalize(temporal_values={})
        assert "amount" not in d

    def test_missing_temporal_values_leaves_amount_absent(self):
        d = self.normalize()
        assert "amount" not in d
