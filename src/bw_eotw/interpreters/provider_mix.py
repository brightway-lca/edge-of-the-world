import math
from collections.abc import Iterator

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import Interpreter, _to_node_id, register


@register("provider_mix")
class ProviderMixInterpreter(Interpreter):
    """Expand a single product demand into one entry per provider.

    Edge data must contain ``product_name``, ``amount``, and ``mix``.
    ``mix`` is a list of dicts each with an integer ``input`` node ID and a
    ``share`` fraction::

        {
            "interpreter": "provider_mix",
            "product_name": "electricity",
            "amount": 2.0,
            "mix": [
                {"input": 101, "share": 0.40},
                {"input": 102, "share": 0.35},
                {"input": 103, "share": 0.25},
            ],
        }

    A bw2data ``Node`` instance may be passed as ``input``; it is converted to
    its integer ID by ``normalize`` before the edge is saved.

    All ``mix`` inputs must be from the same database as ``edge_data["input"]``.

    Yields one ``MatrixEntry`` per provider.  The config is ignored.
    """

    def __call__(self, edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
        col = edge_data["col"]
        amount = edge_data["amount"]
        flip = edge_data.get("flip", False)

        for provider in edge_data["mix"]:
            yield MatrixEntry(
                row=provider["input"],
                col=col,
                amount=amount * provider["share"],
                flip=flip,
            )

    def iter_node_ids(self, edge_data: dict) -> Iterator[int]:
        for provider in edge_data.get("mix", []):
            node_id = provider.get("input")
            if isinstance(node_id, int):
                yield node_id

    def normalize(self, edge_data: dict) -> None:
        """Convert any Node instances in ``mix`` to integer IDs in-place."""
        mix = edge_data.get("mix")
        if not mix:
            return
        for provider in mix:
            if "input" in provider:
                provider["input"] = _to_node_id(provider["input"])

    def validate(self, edge_data: dict) -> None:
        if not edge_data.get("product_name"):
            raise ValueError("provider_mix edge must have a non-empty 'product_name'")

        mix = edge_data.get("mix")
        if not mix:
            raise ValueError("provider_mix edge must have a non-empty 'mix'")

        for i, provider in enumerate(mix):
            if "input" not in provider:
                raise ValueError(f"mix[{i}] is missing required key 'input'")
            if not isinstance(provider["input"], int):
                raise ValueError(
                    f"mix[{i}] 'input' must be an integer node ID, "
                    f"got {type(provider['input']).__name__} — "
                    f"call normalize_edge() before validate_edge(), or use "
                    f"RichEdge.save() which normalizes automatically"
                )
            share = provider.get("share")
            if share is None:
                raise ValueError(f"mix[{i}] is missing required key 'share'")
            if not (0.0 <= share <= 1.0):
                raise ValueError(
                    f"mix[{i}] share must be between 0 and 1 (inclusive), got {share}"
                )

        total = sum(p["share"] for p in mix)
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(f"mix shares must sum to 1, got {total:.8f}")

        super().validate(edge_data)
