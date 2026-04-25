from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import Interpreter, register


@register("standard")
class StandardInterpreter(Interpreter):
    """Single-cell behaviour identical to a plain bw2data exchange."""

    def __call__(self, edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
        yield MatrixEntry.from_edge_value(edge_data, edge_data)

    def iter_node_ids(self, edge_data: dict) -> Iterator[int]:
        yield from ()
