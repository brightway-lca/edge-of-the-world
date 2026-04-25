import dataclasses
import math


@dataclasses.dataclass(frozen=True)
class MatrixEntry:
    """A single realised input value destined for a matrix cell.

    Multiple instances with the same (row, col) are summed during matrix
    construction, so this is not necessarily the final cell value.

    Field names and defaults match those expected by bw_processing's
    ``dictionary_formatter``.  Convert to a plain dict with ``as_dict()``
    before passing to bw_processing.
    """

    row: int
    col: int
    amount: float
    flip: bool = False
    uncertainty_type: int = 0
    loc: float = math.nan
    scale: float = math.nan
    shape: float = math.nan
    minimum: float = math.nan
    maximum: float = math.nan
    negative: bool = False

    def as_dict(self) -> dict:
        return dataclasses.asdict(self)

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
