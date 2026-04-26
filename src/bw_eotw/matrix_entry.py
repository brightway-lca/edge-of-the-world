import math

from bw_processing import MatrixEntry as _MatrixEntry


class MatrixEntry(_MatrixEntry):
    """Extends :class:`bw_processing.MatrixEntry` with a domain-specific constructor."""

    @classmethod
    def from_edge_value(cls, value: dict | float, edge_data: dict) -> "MatrixEntry":
        """Construct from a per-year (or similar) value plus surrounding edge data.

        *value* is either a plain number or an uncertainty dict (same convention
        as bw2data's ``as_uncertainty_dict``).  Row, col, and flip are taken
        from *edge_data*.
        """
        if not isinstance(value, dict):
            value = {"amount": float(value)}
        amount = value["amount"]
        return cls(
            row=edge_data["row"],
            col=edge_data["col"],
            amount=amount,
            flip=edge_data.get("flip", False),
            uncertainty_type=value.get("uncertainty_type", 0),
            loc=value.get("loc", amount),
            scale=value.get("scale", math.nan),
            shape=value.get("shape", math.nan),
            minimum=value.get("minimum", math.nan),
            maximum=value.get("maximum", math.nan),
            negative=value.get("negative", False),
        )
