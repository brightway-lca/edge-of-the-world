from collections.abc import Callable, Iterator

from bw_eotw.matrix_entry import MatrixEntry

# ── shared HTML helpers available to all Interpreter subclasses ──────────────
_HTML_TD = 'style="padding:3px 8px;border:1px solid #dee2e6"'
_HTML_TH = 'style="padding:3px 8px;border:1px solid #dee2e6;background:#f8f9fa;font-weight:bold"'


def _fmt_amount(value) -> str:
    """Format a scalar or uncertainty dict as a short string."""
    if not isinstance(value, dict):
        return str(value)
    amt = value.get("amount", "?")
    ut  = value.get("uncertainty_type", 0)
    return f"{amt} (ut={ut})" if ut else str(amt)


def _to_node_id(value) -> int:
    """Convert an integer or bw2data Node instance to an integer node ID."""
    if isinstance(value, int):
        return value
    try:
        return int(value.id)
    except AttributeError:
        raise TypeError(
            f"Expected an integer node ID or a bw2data Node, "
            f"got {type(value).__name__}"
        )


def _get_node_database(node_id: int) -> str:
    """Return the database name for the given node ID.

    Separated from ``validate`` so tests can patch it without touching the ORM.
    Raises ``ValueError`` if no node with that ID exists.
    """
    from bw2data.backends.schema import ActivityDataset

    try:
        return ActivityDataset.get(ActivityDataset.id == node_id).database
    except ActivityDataset.DoesNotExist:
        raise ValueError(f"No node found with id {node_id}")


class Interpreter:
    """Base class for all edge interpreters.

    Subclassing is not required — duck typing is supported.  Any object
    registered via ``@register`` that implements ``__call__``,
    ``iter_node_ids``, ``normalize``, and ``validate`` with compatible
    signatures will work.  This class provides the default ``normalize``
    (no-op) and the same-database ``validate``; subclass to inherit them.

    Concrete implementations must provide ``__call__`` (interpreter logic) and
    ``iter_node_ids`` (every extra integer node ID embedded in the edge data,
    beyond the standard ``input`` field managed by bw2data).

    The base ``validate`` enforces the same-database invariant: every ID
    returned by ``iter_node_ids`` must belong to the same database as
    ``edge_data["input"]``.  This guarantees that the ``input_database``
    column written to ``ExchangeDataset`` is a correct dependency marker
    even when the interpreter expands one edge into multiple matrix rows.

    Subclasses with additional structural constraints should override
    ``validate``, run their own checks first, then call ``super().validate()``.

    Subclasses that embed node references beyond ``input`` must override
    ``normalize`` to convert any bw2data Node instances to integer IDs
    in-place before the edge is saved.

    Set ``requires_config = True`` on subclasses whose ``__call__`` cannot
    produce a result without a non-empty config dict.  ``resolve()`` will raise
    ``ValueError`` before invoking such an interpreter when no config is active.
    """

    requires_config: bool = False

    def __call__(self, edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
        raise NotImplementedError

    def iter_node_ids(self, edge_data: dict) -> Iterator[int]:
        """Yield every integer node ID this interpreter edge may reference.

        Only yield IDs for references *embedded inside interpreter-specific
        fields* (e.g. ``mix`` entries in ``provider_mix``).  The standard
        ``input`` node is already tracked by bw2data and must not be repeated
        here.

        Yield nothing for interpreters whose only node reference is the
        standard ``input`` field.
        """
        raise NotImplementedError

    def normalize(self, edge_data: dict) -> None:
        """Convert bw2data Node instances to integer IDs in-place.

        Called before ``validate`` and before the edge is written to the
        database.  The default implementation does nothing; subclasses that
        store node references in interpreter-specific fields must override this.
        """

    def repr_parts(self, edge_data: dict) -> list[str]:
        """Extra ``key=value`` strings appended to ``RichEdge.__repr__``.

        Return a list of already-formatted strings, e.g.
        ``["amount=1.5", "years=[2010, 2020]"]``.
        """
        return []

    def html_rows(self, edge_data: dict) -> str:
        """HTML ``<tr>`` rows for the interpreter-specific section of
        ``RichEdge._repr_html_``.

        Return a raw HTML string of zero or more ``<tr>…</tr>`` elements.
        Use the module-level ``_HTML_TD`` / ``_HTML_TH`` CSS constants and
        ``_fmt_amount`` for consistent styling.
        """
        return ""

    def validate(self, edge_data: dict) -> None:
        """Enforce the same-database invariant across all node references."""
        if edge_data.get("input") is None:
            raise ValueError("Interpreter edge must have an 'input' field")
        node_ids = list(self.iter_node_ids(edge_data))
        if not node_ids:
            return
        expected_db = _get_node_database(edge_data["input"])
        for node_id in node_ids:
            node_db = _get_node_database(node_id)
            if node_db != expected_db:
                raise ValueError(
                    f"Node {node_id} is in database '{node_db}', but the edge "
                    f"'input' is from '{expected_db}'. All node references in "
                    f"an interpreter edge must come from the same database."
                )


_REGISTRY: dict[str, Interpreter] = {}


def register(name: str) -> Callable[[type], type]:
    """Class decorator that registers an ``Interpreter`` subclass under *name*.

    Usage::

        @register("my_interpreter")
        class MyInterpreter(Interpreter):
            ...
    """
    def decorator(cls: type) -> type:
        _REGISTRY[name] = cls()
        return cls
    return decorator


def normalize_edge(edge_data) -> None:
    """Convert Node instances to integer IDs in interpreter-specific fields.

    Modifies *edge_data* in-place.  Accepts either a plain dict or any
    mapping-like object that supports ``get`` and ``__setitem__`` (e.g. a
    bw2data Exchange proxy).  Silently does nothing for edges without an
    ``interpreter`` key or for unknown interpreter names.
    """
    name = edge_data.get("interpreter")
    if name is None:
        return
    interpreter = _REGISTRY.get(name)
    if interpreter is not None:
        interpreter.normalize(edge_data)


def validate_edge(edge_data: dict) -> None:
    """Run the registered interpreter's validator for this edge, if any.

    Silently does nothing for edges without an ``interpreter`` key or for
    unknown interpreter names.  Raises ``ValueError`` when validation fails.
    """
    name = edge_data.get("interpreter")
    if name is None:
        return
    interpreter = _REGISTRY.get(name)
    if interpreter is not None:
        interpreter.validate(edge_data)


def resolve(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    """Dispatch *edge_data* to its registered interpreter.

    Raises ``KeyError`` for unknown interpreter names.
    Raises ``ValueError`` when the interpreter requires a non-empty config and
    none is active.
    """
    name = edge_data["interpreter"]
    try:
        interpreter = _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"No interpreter registered for '{name}'. "
            f"Registered interpreters: {sorted(_REGISTRY)}"
        )
    if interpreter.requires_config and not config:
        raise ValueError(
            f"Interpreter '{name}' requires a config but none is active. "
            f"Call set_config(db_name, config) before processing."
        )
    yield from interpreter(edge_data, config)
