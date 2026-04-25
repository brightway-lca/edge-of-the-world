import math
from collections.abc import Iterator

from bw2data import get_id

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import register, register_validator


@register("provider_mix")
def provider_mix(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    """Expand a single product demand into one entry per provider.

    Edge data must contain ``product_name``, ``amount``, and ``mix``.
    ``mix`` is a list of dicts each with an ``input`` key (a
    ``(database, code)`` tuple) and a ``share`` fraction::

        {
            "interpreter": "provider_mix",
            "product_name": "electricity",
            "amount": 2.0,
            "mix": [
                {"input": ("grid", "wind"),  "share": 0.40},
                {"input": ("grid", "solar"), "share": 0.35},
                {"input": ("grid", "gas"),   "share": 0.25},
            ],
        }

    Yields one ``MatrixEntry`` per provider.  Each entry has the provider's
    node ID as ``row``, the edge's ``col``, and ``amount * share`` as the
    amount.  The config is ignored.
    """
    col = edge_data["col"]
    amount = edge_data["amount"]
    flip = edge_data.get("flip", False)

    for provider in edge_data["mix"]:
        yield MatrixEntry(
            row=get_id(provider["input"]),
            col=col,
            amount=amount * provider["share"],
            flip=flip,
        )


@register_validator("provider_mix")
def validate_provider_mix(edge_data: dict) -> None:
    """Validate product_name, mix entries, share bounds, and share sum."""
    if not edge_data.get("product_name"):
        raise ValueError("provider_mix edge must have a non-empty 'product_name'")

    mix = edge_data.get("mix")
    if not mix:
        raise ValueError("provider_mix edge must have a non-empty 'mix'")

    for i, provider in enumerate(mix):
        if "input" not in provider:
            raise ValueError(f"mix[{i}] is missing required key 'input'")
        share = provider.get("share")
        if share is None:
            raise ValueError(f"mix[{i}] is missing required key 'share'")
        if not (0.0 <= share <= 1.0):
            raise ValueError(
                f"mix[{i}] share must be between 0 and 1 (inclusive), got {share}"
            )

    total = sum(p["share"] for p in mix)
    if not math.isclose(total, 1.0, abs_tol=1e-9):
        raise ValueError(
            f"mix shares must sum to 1, got {total:.8f}"
        )
