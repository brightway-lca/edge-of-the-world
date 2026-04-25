from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import register


@register("standard")
def standard(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    """Single-cell behaviour identical to a plain bw2data exchange."""
    yield MatrixEntry.from_edge_value(edge_data, edge_data)
