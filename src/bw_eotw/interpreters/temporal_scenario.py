from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import register, register_validator


@register("temporal_scenario")
def temporal_scenario(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    """Select a value by scenario name and then by year.

    Edge data must contain ``scenario_temporal_values``, a nested dict keyed
    first by scenario name and then by integer year.  Each leaf value may be a
    plain number or an uncertainty dict::

        {
            "interpreter": "temporal_scenario",
            "scenario_temporal_values": {
                "baseline":   {2020: 1.00, 2030: 0.85},
                "optimistic": {2020: 0.80, 2030: {"amount": 0.60, "uncertainty_type": 2, "scale": 0.05}},
            },
            "default_year": 2020,   # optional
        }

    Scenario selection (strict, like the ``scenario`` interpreter):
    ``config["scenario"]`` must be present and match a key in
    ``scenario_temporal_values``; a ``KeyError`` is raised otherwise.

    Year selection within the scenario (like the ``temporal`` interpreter):
    ``config["year"]`` is tried first; if absent or not found, ``default_year``
    from the edge data is used; a ``KeyError`` is raised if neither works.
    """
    all_values: dict = edge_data["scenario_temporal_values"]
    default_year = edge_data.get("default_year")

    # --- scenario (strict) ---
    if "scenario" not in config:
        raise KeyError(
            f"config is missing required key 'scenario'. "
            f"Available scenarios: {sorted(all_values)}"
        )
    scenario = config["scenario"]
    if scenario not in all_values:
        raise KeyError(
            f"Scenario '{scenario}' not found. "
            f"Available scenarios: {sorted(all_values)}"
        )

    # --- year within scenario (with optional default) ---
    values: dict = all_values[scenario]
    year = config.get("year")

    value = values.get(year) if year is not None else None
    if value is None and default_year is not None:
        value = values.get(default_year)

    if value is None:
        tried = []
        if year is not None:
            tried.append(f"year={year} (from config)")
        if default_year is not None:
            tried.append(f"default_year={default_year} (from edge)")
        if not tried:
            tried.append("no 'year' in config and no 'default_year' in edge data")
        raise KeyError(
            f"No temporal value for scenario '{scenario}' "
            f"(tried: {', '.join(tried)}). "
            f"Available years: {sorted(values)}"
        )

    yield MatrixEntry.from_edge_value(value, edge_data)


@register_validator("temporal_scenario")
def validate_temporal_scenario(edge_data: dict) -> None:
    """Validate scenario_temporal_values and optional default_year."""
    all_values = edge_data.get("scenario_temporal_values")
    if not all_values:
        raise ValueError(
            "temporal_scenario edge must have a non-empty 'scenario_temporal_values'"
        )
    for scenario, values in all_values.items():
        if not values:
            raise ValueError(
                f"scenario '{scenario}' must have at least one temporal value"
            )
    default_year = edge_data.get("default_year")
    if default_year is not None:
        for scenario, values in all_values.items():
            if default_year not in values:
                raise ValueError(
                    f"default_year {default_year} not present in scenario '{scenario}'. "
                    f"Available years: {sorted(values)}"
                )
