from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import Interpreter, register


@register("loss")
class LossInterpreter(Interpreter):
    """Expand a single edge into a main flow and a separate loss component.

    Edge data must contain ``amount`` (a plain number) and ``loss_factor``
    (a plain number between 0 and 1)::

        {
            "interpreter": "loss",
            "amount": 1.0,
            "loss_factor": 0.05,
        }

    Uncertainty in either ``amount`` or ``loss_factor`` is not supported.
    The main flow and the loss are correlated (both depend on the same
    underlying quantity), so sampling them independently would give wrong
    totals.  Correlated sampling is not yet implemented.

    Yields two MatrixEntry objects with the same (row, col):

    1. The main flow with ``amount`` and no uncertainty.
    2. The loss flow with ``amount * loss_factor`` and no uncertainty.

    Both entries are summed into the same matrix cell by bw_processing,
    giving a total of ``amount * (1 + loss_factor)``.
    """

    def __call__(self, edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
        amount = float(edge_data["amount"])
        loss_factor = float(edge_data["loss_factor"])

        yield MatrixEntry(
            row=edge_data["row"],
            col=edge_data["col"],
            amount=amount,
            flip=edge_data.get("flip", False),
        )
        yield MatrixEntry(
            row=edge_data["row"],
            col=edge_data["col"],
            amount=amount * loss_factor,
            flip=edge_data.get("flip", False),
        )

    def iter_node_ids(self, edge_data: dict) -> Iterator[int]:
        yield from ()

    def validate(self, edge_data: dict) -> None:
        if edge_data.get("uncertainty_type", 0) != 0:
            raise ValueError(
                "loss edges do not support uncertainty on 'amount'. "
                "Uncertainty requires correlated sampling, which is not yet implemented."
            )

        raw = edge_data.get("loss_factor")
        if raw is None:
            raise ValueError("loss edge is missing required field 'loss_factor'")
        if isinstance(raw, dict):
            raise ValueError(
                "loss_factor must be a plain number, not an uncertainty dict. "
                "Uncertainty requires correlated sampling, which is not yet implemented."
            )
        amount = float(raw)
        if not (0.0 <= amount <= 1.0):
            raise ValueError(
                f"loss_factor must be between 0 and 1 (inclusive), got {amount}"
            )
        super().validate(edge_data)
