from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import Interpreter, register


@register("temporal")
class TemporalInterpreter(Interpreter):
    """Select a value by year, with an optional per-edge default year.

    Edge data must contain ``temporal_values``, a dict keyed by integer year.
    Each value may be a plain number or an uncertainty dict::

        {
            "interpreter": "temporal",
            "temporal_values": {
                2010: 0.3,
                2020: {"amount": 0.4, "uncertainty_type": 2, "scale": 0.05},
                2030: 0.6,
            },
            "default_year": 2020,   # optional — used when config year is absent or not found
        }

    Year selection order:

    1. ``config["year"]`` if present and in ``temporal_values``.
    2. ``edge_data["default_year"]`` if present and in ``temporal_values``.
    3. ``KeyError`` otherwise, listing the available years.
    """

    def __call__(self, edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
        values: dict = edge_data["temporal_values"]
        year = config.get("year")
        default_year = edge_data.get("default_year")

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
                f"No temporal value found (tried: {', '.join(tried)}). "
                f"Available years: {sorted(values)}"
            )

        yield MatrixEntry.from_edge_value(value, edge_data)

    def iter_node_ids(self, edge_data: dict) -> Iterator[int]:
        yield from ()
