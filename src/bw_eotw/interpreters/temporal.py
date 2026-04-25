from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import register

DEFAULT_TEMPORAL_YEAR = 2020


@register("temporal")
def temporal(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    """Select a value by year, falling back to DEFAULT_TEMPORAL_YEAR (2020).

    Edge data must contain a ``temporal_values`` dict keyed by integer year.
    Each value may be a plain number or an uncertainty dict::

        {
            "interpreter": "temporal",
            "temporal_values": {
                2010: 0.3,
                2020: {"amount": 0.4, "uncertainty_type": 2, "scale": 0.05},
                2030: 0.6,
            },
        }

    If ``config["year"]`` is not present in ``temporal_values``, the value for
    ``DEFAULT_TEMPORAL_YEAR`` is used.  A ``KeyError`` is raised if neither the
    requested year nor the fallback year is available.
    """
    year = config.get("year", DEFAULT_TEMPORAL_YEAR)
    values: dict = edge_data["temporal_values"]
    value = values.get(year, values.get(DEFAULT_TEMPORAL_YEAR))
    if value is None:
        raise KeyError(
            f"No temporal value for year {year} and no {DEFAULT_TEMPORAL_YEAR} "
            f"fallback. Available years: {sorted(values)}"
        )
    yield MatrixEntry.from_edge_value(value, edge_data)
