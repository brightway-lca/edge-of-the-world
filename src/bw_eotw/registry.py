from collections.abc import Callable, Iterator

from bw_eotw.matrix_entry import MatrixEntry


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

    Subclasses must implement ``__call__`` (interpreter logic) and
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
    """

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

    def validate(self, edge_data: dict) -> None:
        """Enforce the same-database invariant across all node references."""
        edge_input = edge_data.get("input")
        if edge_input is None:
            raise ValueError("Interpreter edge must have an 'input' field")
        expected_db = edge_input[0]
        for node_id in self.iter_node_ids(edge_data):
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
    """
    name = edge_data["interpreter"]
    try:
        interpreter = _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"No interpreter registered for '{name}'. "
            f"Registered interpreters: {sorted(_REGISTRY)}"
        )
    yield from interpreter(edge_data, config)
