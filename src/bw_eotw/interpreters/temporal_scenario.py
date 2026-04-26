from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import Interpreter, _HTML_TD, _HTML_TH, _fmt_amount, register


@register("temporal_scenario")
class TemporalScenarioInterpreter(Interpreter):
    requires_config = True

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

    def __call__(self, edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
        all_values: dict = edge_data["scenario_temporal_values"]
        default_year = edge_data.get("default_year")

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

    def normalize(self, edge_data: dict) -> None:
        if "amount" not in edge_data:
            edge_data["amount"] = 1.0

    def iter_node_ids(self, edge_data: dict) -> Iterator[int]:
        yield from ()

    def repr_parts(self, edge_data: dict) -> list[str]:
        all_values = edge_data.get("scenario_temporal_values") or {}
        all_years = sorted({y for tv in all_values.values() for y in tv})
        return [
            f"scenarios={sorted(all_values)}",
            f"years={all_years}",
        ]

    def html_rows(self, edge_data: dict) -> str:
        all_values  = edge_data.get("scenario_temporal_values") or {}
        default_year = edge_data.get("default_year")
        scenarios = sorted(all_values)
        all_years = sorted({y for tv in all_values.values() for y in tv})
        rows = ""
        if default_year is not None:
            rows += (
                f'<tr><td {_HTML_TH}>default_year</td>'
                f'<td {_HTML_TD}>{default_year}</td></tr>'
            )
        header = "".join(f'<th {_HTML_TH}>{y}</th>' for y in all_years)
        grid = "".join(
            f'<tr><td {_HTML_TH}>{s}</td>'
            + "".join(
                f'<td {_HTML_TD}>'
                f'{_fmt_amount(all_values[s][y]) if y in all_values[s] else "—"}'
                f'</td>'
                for y in all_years
            )
            + "</tr>"
            for s in scenarios
        )
        rows += (
            f'<tr><td {_HTML_TH}>scenario_temporal_values<br>'
            f'<small style="font-weight:normal">'
            f'({len(scenarios)} scenarios × {len(all_years)} years)</small></td>'
            f'<td {_HTML_TD}>'
            f'<table style="border-collapse:collapse">'
            f'<tr><th {_HTML_TH}></th>{header}</tr>'
            f'{grid}'
            f'</table></td></tr>'
        )
        return rows

    def validate(self, edge_data: dict) -> None:
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
        super().validate(edge_data)
