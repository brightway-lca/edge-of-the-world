import pytest

from bw_eotw.registry import resolve

BASE_EDGE = {"row": 10, "col": 20, "flip": False}


def edge(**kwargs):
    return {**BASE_EDGE, **kwargs}


class TestRequiresConfig:
    """Interpreters with requires_config=True raise ValueError when config is empty."""

    def test_scenario_empty_config_raises_value_error(self):
        edge_data = edge(
            interpreter="scenario",
            scenario_values={"baseline": 1.0},
        )
        with pytest.raises(ValueError, match="requires a config"):
            list(resolve(edge_data, {}))

    def test_temporal_scenario_empty_config_raises_value_error(self):
        edge_data = edge(
            interpreter="temporal_scenario",
            scenario_temporal_values={"baseline": {2020: 1.0}},
        )
        with pytest.raises(ValueError, match="requires a config"):
            list(resolve(edge_data, {}))

    def test_temporal_empty_config_does_not_raise(self):
        edge_data = edge(
            interpreter="temporal",
            temporal_values={2020: 0.5},
            default_year=2020,
        )
        entries = list(resolve(edge_data, {}))
        assert len(entries) == 1

    def test_provider_mix_empty_config_does_not_raise(self):
        edge_data = edge(
            interpreter="provider_mix",
            product_name="electricity",
            amount=1.0,
            mix=[{"input": 10, "share": 1.0}],
        )
        entries = list(resolve(edge_data, {}))
        assert len(entries) == 1

    def test_scenario_with_config_does_not_raise(self):
        edge_data = edge(
            interpreter="scenario",
            scenario_values={"baseline": 1.0},
        )
        entries = list(resolve(edge_data, {"scenario": "baseline"}))
        assert entries[0].amount == pytest.approx(1.0)

    def test_temporal_scenario_with_config_does_not_raise(self):
        edge_data = edge(
            interpreter="temporal_scenario",
            scenario_temporal_values={"baseline": {2020: 0.9}},
        )
        entries = list(resolve(edge_data, {"scenario": "baseline", "year": 2020}))
        assert entries[0].amount == pytest.approx(0.9)
