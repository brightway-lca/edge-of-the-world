from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import Interpreter, _HTML_TD, _HTML_TH, register


@register("standard")
class StandardInterpreter(Interpreter):
    """Single-cell behaviour identical to a plain bw2data exchange."""

    def __call__(self, edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
        yield MatrixEntry.from_edge_value(edge_data, edge_data)

    def iter_node_ids(self, edge_data: dict) -> Iterator[int]:
        yield from ()

    def repr_parts(self, edge_data: dict) -> list[str]:
        parts = [f"amount={edge_data.get('amount', '?')}"]
        if edge_data.get("flip"):
            parts.append("flip=True")
        return parts

    def html_rows(self, edge_data: dict) -> str:
        rows = (
            f'<tr><td {_HTML_TH}>amount</td>'
            f'<td {_HTML_TD}>{edge_data.get("amount", "—")}</td></tr>'
        )
        if edge_data.get("flip"):
            rows += f'<tr><td {_HTML_TH}>flip</td><td {_HTML_TD}>True</td></tr>'
        return rows
