from collections.abc import Iterable

from bw2data.backends import SQLiteBackend

from bw_eotw.node_classes import RichNode
from bw_eotw.registry import resolve


class RichEdgesBackend(SQLiteBackend):
    """Brightway database backend with interpreter-driven edge resolution.

    Edges carrying an ``interpreter`` key are dispatched to the registered
    interpreter, which may yield multiple ``MatrixEntry`` values per edge.
    Edges without that key pass through unchanged, so plain bw2data exchanges
    require no migration.

    Use ``bw2data.Database(name, backend="eotw")`` to create a database that
    uses this backend.  Populate it with ``db.new_node()`` / ``node.new_edge()``
    rather than ``write()``.
    """

    backend = "eotw"
    node_class = RichNode

    def register(self, **kwargs):
        """Register the database without writing an empty datapackage.

        The parent ``register()`` calls ``write({})`` to initialise the
        datapackage file, but ``write()`` is disabled on this backend.
        Passing ``write_empty=False`` skips that step; the datapackage is
        created on the first call to ``process()``.
        """
        super().register(write_empty=False, **kwargs)

    def write(self, data, **kwargs):
        raise NotImplementedError(
            "RichEdgesBackend does not support write(). "
            "Use individual node and edge methods instead."
        )

    def _efficient_write_many_data(self, data, **kwargs):
        raise NotImplementedError(
            "RichEdgesBackend does not support write(). "
            "Use individual node and edge methods instead."
        )

    def process(self, config: dict | None = None, **kwargs):
        """Build the processed datapackage, resolving edges with *config*.

        *config* is an arbitrary dict passed to every interpreter (e.g.
        ``{"year": 2030}``).  Pass ``None`` to use an empty config.
        """
        self._process_config = config or {}
        try:
            super().process(**kwargs)
        finally:
            del self._process_config

    def exchange_data_iterator(self, qs_func, dependents: set, flip: bool = False) -> Iterable:
        for edge_data in super().exchange_data_iterator(qs_func, dependents, flip):
            if "interpreter" not in edge_data:
                yield edge_data
            else:
                for entry in resolve(edge_data, self._process_config):
                    yield entry.as_dict()
