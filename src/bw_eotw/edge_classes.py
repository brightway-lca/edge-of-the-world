from bw2data.backends.proxies import Exchange, Exchanges

from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.registry import normalize_edge, resolve, validate_edge


class RichEdge(Exchange):
    """An exchange that can be resolved to one or more matrix input values.

    The ``interpreter`` key in the edge data selects which registered
    interpreter handles resolution.  Edges without that key behave exactly
    like standard bw2data exchanges and require no migration.
    """

    @property
    def interpreter(self) -> str | None:
        return self.get("interpreter")

    def save(self, signal: bool = True, data_already_set: bool = False, force_insert: bool = False):
        normalize_edge(self)
        validate_edge(dict(self))
        return super().save(signal=signal, data_already_set=data_already_set, force_insert=force_insert)

    def resolve(self, config: dict | None = None) -> list[MatrixEntry]:
        """Return the realised matrix input values for this edge.

        Requires the edge to have an ``interpreter`` key.  Use this method
        for inspection and testing; matrix building goes through the backend's
        ``exchange_data_iterator`` override instead.
        """
        return list(resolve(dict(self), config or {}))


class RichEdges(Exchanges):
    def __iter__(self):
        for obj in self._get_queryset():
            yield RichEdge(obj)
