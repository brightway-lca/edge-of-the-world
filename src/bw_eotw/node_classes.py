from bw2data.backends.proxies import Activity
from bw2data.configuration import labels

from bw_eotw.edge_classes import RichEdge, RichEdges


class RichNode(Activity):
    """A node in a `RichEdgesBackend` database.

    Returns `RichEdge` objects when iterating over exchanges so that callers
    can access rich edge metadata (e.g. `matrix_contributions`).
    """

    def new_edge(self, **kwargs) -> "RichEdge":
        """Create a new :class:`RichEdge` linked to this node.

        Overrides the parent implementation so that :meth:`RichEdge.save`
        (which calls ``normalize_edge`` and ``validate_edge``) is used instead
        of the plain ``Exchange.save``.
        """
        exc = RichEdge()
        exc["output"] = self.key
        for key, value in kwargs.items():
            exc[key] = value
        return exc

    def exchanges(self, exchanges_class=None):
        return super().exchanges(exchanges_class=exchanges_class or RichEdges)

    def technosphere(self, exchanges_class=None):
        return super().technosphere(exchanges_class=exchanges_class or RichEdges)

    def biosphere(self, exchanges_class=None):
        return super().biosphere(exchanges_class=exchanges_class or RichEdges)

    def production(self, include_substitution=False, exchanges_class=None):
        return super().production(
            include_substitution=include_substitution,
            exchanges_class=exchanges_class or RichEdges,
        )

    def substitution(self, exchanges_class=None):
        return super().substitution(exchanges_class=exchanges_class or RichEdges)

    def upstream(self, kinds=None, exchanges_class=None):
        kinds = kinds if kinds is not None else labels.technosphere_negative_edge_types
        return super().upstream(kinds=kinds, exchanges_class=exchanges_class or RichEdges)
