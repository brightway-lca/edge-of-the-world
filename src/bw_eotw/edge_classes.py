from bw2data.backends.proxies import Exchange, Exchanges
from bw2data.backends.schema import get_id

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import _REGISTRY, normalize_edge, resolve, validate_edge

_COLORS = {
    "singlevalue":       "#6c757d",
    "temporal":          "#0d6efd",
    "scenario":          "#198754",
    "provider_mix":      "#fd7e14",
    "temporal_scenario": "#6f42c1",
    "loss":              "#dc3545",
}
_DEFAULT_COLOR = "#adb5bd"

_TD = 'style="padding:3px 8px;border:1px solid #dee2e6"'
_TH = 'style="padding:3px 8px;border:1px solid #dee2e6;background:#f8f9fa;font-weight:bold"'



class RichEdge(Exchange):
    """An exchange that can be resolved to one or more matrix input values.

    The ``interpreter`` key in the edge data selects which registered
    interpreter handles resolution.  Edges without that key behave exactly
    like standard bw2data exchanges and require no migration.
    """

    @property
    def interpreter(self) -> str | None:
        return self.get("interpreter")

    def __repr__(self) -> str:
        interp = self.get("interpreter")
        inp = repr(self.input)
        out = repr(self.output)

        if interp is None:
            return (
                f"RichEdge(input={inp}, output={out}, "
                f"amount={self.get('amount', '?')})"
            )

        parts = [f"interpreter={interp!r}", f"input={inp}", f"output={out}"]
        interpreter_obj = _REGISTRY.get(interp)
        if interpreter_obj is not None:
            parts.extend(interpreter_obj.repr_parts(dict(self)))
        return f"RichEdge({', '.join(parts)})"

    def _repr_html_(self) -> str:
        interp = self.get("interpreter")
        color = _COLORS.get(interp, _DEFAULT_COLOR)
        title = f"RichEdge &mdash; <b>{interp}</b>" if interp else "RichEdge"
        data  = dict(self)

        inp = repr(self.input)
        out = repr(self.output)
        common = (
            f'<tr><td {_TH}>input</td>'
            f'<td {_TD}><code>{inp}</code></td></tr>'
            f'<tr><td {_TH}>output</td>'
            f'<td {_TD}><code>{out}</code></td></tr>'
        )

        if interp is None:
            extra = (
                f'<tr><td {_TH}>amount</td>'
                f'<td {_TD}>{self.get("amount", "—")}</td></tr>'
            )
            if self.get("flip"):
                extra += f'<tr><td {_TH}>flip</td><td {_TD}>True</td></tr>'
        else:
            interpreter_obj = _REGISTRY.get(interp)
            extra = interpreter_obj.html_rows(data) if interpreter_obj is not None else ""

        return (
            f'<div style="font-family:monospace;font-size:13px;display:inline-block">'
            f'<div style="background:{color};color:white;padding:4px 10px;'
            f'border-radius:4px 4px 0 0">{title}</div>'
            f'<table style="border-collapse:collapse;border:1px solid {color}">'
            f'{common}{extra}'
            f'</table></div>'
        )

    def save(self, signal: bool = True, data_already_set: bool = False, force_insert: bool = False):
        normalize_edge(self)
        validate_edge(dict(self))
        return super().save(signal=signal, data_already_set=data_already_set, force_insert=force_insert)

    def resolve(self, config: dict | None = None) -> list[MatrixEntry]:
        """Return the realised matrix input values for this edge.

        Requires the edge to have an ``interpreter`` key.  Use this method
        for inspection and testing; matrix building goes through the backend's
        ``exchange_data_iterator`` override instead.

        ``row`` and ``col`` are populated as integer node IDs (matching what
        ``exchange_data_iterator`` provides to interpreters at process time).
        """
        data = dict(self)
        data["row"] = get_id(data["input"])
        data["col"] = get_id(data["output"])
        return list(resolve(data, config or {}))


class RichEdges(Exchanges):
    def __iter__(self):
        for obj in self._get_queryset():
            yield RichEdge(obj)
