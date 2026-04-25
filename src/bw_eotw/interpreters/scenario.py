from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import register, register_validator


@register("scenario")
def scenario(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    """Select a value by scenario name.

    Edge data must contain a ``scenario_values`` dict keyed by scenario name.
    Each value may be a plain number or an uncertainty dict::

        {
            "interpreter": "scenario",
            "scenario_values": {
                "baseline":   1.00,
                "optimistic": {"amount": 0.70, "uncertainty_type": 2, "scale": 0.05},
                "pessimistic": 1.30,
            },
        }

    ``config["scenario"]`` must be present and must match a key in
    ``scenario_values``.  Both missing and unrecognised scenario names raise a
    ``KeyError`` with a message listing the available scenarios.
    """
    values: dict = edge_data["scenario_values"]

    if "scenario" not in config:
        raise KeyError(
            f"config is missing required key 'scenario'. "
            f"Available scenarios: {sorted(values)}"
        )

    name = config["scenario"]
    if name not in values:
        raise KeyError(
            f"Scenario '{name}' not found in edge. "
            f"Available scenarios: {sorted(values)}"
        )

    yield MatrixEntry.from_edge_value(values[name], edge_data)


@register_validator("scenario")
def validate_scenario(edge_data: dict) -> None:
    """Validate that ``scenario_values`` is present and non-empty."""
    values = edge_data.get("scenario_values")
    if not values:
        raise ValueError(
            "scenario edge must have a non-empty 'scenario_values' dict"
        )
