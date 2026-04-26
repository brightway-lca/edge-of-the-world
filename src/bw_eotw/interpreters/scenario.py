from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import Interpreter, _HTML_TD, _HTML_TH, _fmt_amount, register


@register("scenario")
class ScenarioInterpreter(Interpreter):
    requires_config = True

    """Select a value by scenario name.  Requires ``config["scenario"]``.

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

    def __call__(self, edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
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

    def iter_node_ids(self, edge_data: dict) -> Iterator[int]:
        yield from ()

    def repr_parts(self, edge_data: dict) -> list[str]:
        values = edge_data.get("scenario_values") or {}
        return [f"scenarios={sorted(values)}"]

    def html_rows(self, edge_data: dict) -> str:
        values = edge_data.get("scenario_values") or {}
        inner = (
            f'<table style="border-collapse:collapse">'
            f'<tr><th {_HTML_TH}>scenario</th><th {_HTML_TH}>amount</th></tr>'
            + "".join(
                f'<tr><td {_HTML_TD}>{s}</td><td {_HTML_TD}>{_fmt_amount(values[s])}</td></tr>'
                for s in sorted(values)
            )
            + "</table>"
        )
        return (
            f'<tr><td {_HTML_TH}>scenario_values<br>'
            f'<small style="font-weight:normal">({len(values)} scenarios)</small></td>'
            f'<td {_HTML_TD}>{inner}</td></tr>'
        )

    def validate(self, edge_data: dict) -> None:
        values = edge_data.get("scenario_values")
        if not values:
            raise ValueError(
                "scenario edge must have a non-empty 'scenario_values' dict"
            )
        super().validate(edge_data)
