import hashlib
import json

from bw2data import databases
from bw2data.database import Database


def config_hash(config: dict) -> str:
    """Return an 8-character hex digest uniquely identifying *config*."""
    return hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()[:8]


def _apply_config(db_name: str, config: dict | None) -> None:
    """Write *config* into metadata and mark the database dirty if the
    corresponding processed file does not exist yet."""
    if config:
        databases[db_name]["eotw_config"] = config
    else:
        databases[db_name].pop("eotw_config", None)
    databases.flush()

    db = Database(db_name)
    processed_path = db.dirpath_processed() / db.filename_processed()
    if not processed_path.exists():
        databases.set_dirty(db_name)


class set_config:
    """Set the active config for an eotw database and invalidate the cache if needed.

    Stores *config* in database metadata so that ``process()`` and
    ``filename_processed()`` pick it up automatically.  Checks whether the
    corresponding processed datapackage already exists on disk; if not, marks
    the database dirty so the next access triggers a rebuild.

    Pass ``config=None`` to clear any active config and revert to config-less
    behaviour.

    Can be used as a plain call or as a context manager that restores the
    previous config on exit::

        set_config("mydb", {"year": 2030})

        with set_config("mydb", {"year": 2030}):
            fu, data_objs, remapping = bw2data.prepare_lca_inputs(...)
    """

    def __init__(self, db_name: str, config: dict | None) -> None:
        self.db_name = db_name
        self._previous = databases[db_name].get("eotw_config")
        _apply_config(db_name, config)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        _apply_config(self.db_name, self._previous)
