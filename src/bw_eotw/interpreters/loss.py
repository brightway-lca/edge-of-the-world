import math
from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import register, register_validator


def _scale_loss_uncertainty(loss_factor: dict, base_amount: float) -> dict:
    """Scale a loss_factor uncertainty dict by base_amount.

    Distribution parameters that are in the same units as the amount
    (loc, scale, minimum, maximum) are multiplied by base_amount.
    Dimensionless parameters (shape, uncertainty_type, negative) are not.
    """
    scaled = dict(loss_factor)
    loss_amount = base_amount * loss_factor["amount"]
    scaled["amount"] = loss_amount
    if "loc" in loss_factor:
        scaled["loc"] = base_amount * loss_factor["loc"]
    else:
        scaled["loc"] = loss_amount
    for field in ("scale", "minimum", "maximum"):
        if field in loss_factor and not math.isnan(loss_factor[field]):
            scaled[field] = base_amount * loss_factor[field]
    return scaled


@register("loss")
def loss(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    """Expand a single edge into a main flow and a separate loss component.

    Edge data must contain ``loss_factor``, either a plain number or an
    uncertainty dict (same convention as bw2data's ``as_uncertainty_dict``)::

        {
            "interpreter": "loss",
            "amount": 1.0,
            "loss_factor": 0.05,
        }

    Yields two MatrixEntry objects with the same (row, col):

    1. The main flow with ``amount`` and its uncertainty from the edge.
    2. The loss flow with ``amount * loss_factor`` and uncertainty scaled
       proportionally from ``loss_factor``'s own uncertainty fields.

    Both entries are summed into the same matrix cell by bw_processing,
    giving a total of ``amount * (1 + loss_factor)``.
    """
    loss_factor = edge_data["loss_factor"]
    if not isinstance(loss_factor, dict):
        loss_factor = {"amount": float(loss_factor)}

    yield MatrixEntry.from_edge_value(edge_data, edge_data)

    loss_value = _scale_loss_uncertainty(loss_factor, edge_data["amount"])
    yield MatrixEntry.from_edge_value(loss_value, edge_data)


@register_validator("loss")
def validate_loss(edge_data: dict) -> None:
    """Validate that ``loss_factor`` is a number in [0, 1].

    Accepts either a plain number or an uncertainty dict; in the latter case
    the ``amount`` field (the central value) is checked.
    """
    raw = edge_data.get("loss_factor")
    if raw is None:
        raise ValueError("loss edge is missing required field 'loss_factor'")

    amount = raw["amount"] if isinstance(raw, dict) else float(raw)

    if not (0.0 <= amount <= 1.0):
        raise ValueError(
            f"loss_factor must be between 0 and 1 (inclusive), got {amount}"
        )
