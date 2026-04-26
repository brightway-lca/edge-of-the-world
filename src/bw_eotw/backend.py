from collections.abc import Iterable

from bw2data.backends import SQLiteBackend
from bw_processing import clean_datapackage_name

from bw_eotw.config import config_hash, set_config as _set_config
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

    def set_config(self, config: dict | None):
        """Set the active config for this database; returns a context manager.

        Delegates to the module-level :class:`set_config`, passing ``self.name``
        automatically::

            db.set_config({"year": 2030})

            with db.set_config({"year": 2030}):
                fu, data_objs, _ = bw2data.prepare_lca_inputs(...)
        """
        return _set_config(self.name, config)

    def filename_processed(self):
        config = self.metadata.get("eotw_config") or {}
        if not config:
            return super().filename_processed()
        h = config_hash(config)
        return clean_datapackage_name(f"{self.filename}_{h}.zip")

    def process(self, **kwargs):
        """Build the processed datapackage, resolving edges with *config*.

        After writing the datapackage for the active config, any other
        config-hashed zips for this database are deleted.  They are stale:
        ``process()`` is only called when the database is dirty (contents
        changed), which invalidates every previously cached config variant.
        """
        self._process_config = self.metadata.get("eotw_config") or {}
        try:
            super().process(**kwargs)
        finally:
            self._purge_stale_config_zips()
            del self._process_config

    def _purge_stale_config_zips(self):
        """Delete all stale datapackage variants for this database.

        Deletes every other config-hashed zip.  When a config-specific zip was
        just written (i.e. the current filename differs from the base filename),
        also deletes the base zip: it was produced by a different database state
        and must not be loaded by a subsequent no-config LCA call.
        """
        current = self.filename_processed()
        base = super().filename_processed()
        for path in self.dirpath_processed().glob(f"{self.filename}_*.zip"):
            if path.name != current:
                path.unlink(missing_ok=True)
        if current != base:
            base_path = self.dirpath_processed() / base
            if base_path.exists():
                base_path.unlink(missing_ok=True)

    def exchange_data_iterator(self, qs_func, dependents: set, flip: bool = False) -> Iterable:
        for edge_data in super().exchange_data_iterator(qs_func, dependents, flip):
            if "interpreter" not in edge_data:
                yield edge_data
            else:
                for entry in resolve(edge_data, self._process_config):
                    yield entry.as_dict()
