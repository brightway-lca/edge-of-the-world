from collections.abc import Callable, Iterator

from bw_eotw.matrix_entry import MatrixEntry

InterpreterFn = Callable[[dict, dict], Iterator[MatrixEntry]]
ValidatorFn = Callable[[dict], None]

_REGISTRY: dict[str, InterpreterFn] = {}
_VALIDATORS: dict[str, ValidatorFn] = {}


def register(name: str) -> Callable[[InterpreterFn], InterpreterFn]:
    """Decorator that registers a function as a named edge interpreter.

    An interpreter has signature ``(edge_data: dict, config: dict) ->
    Iterator[MatrixEntry]`` and is responsible for turning one edge's data
    into zero or more realised matrix input values.
    """
    def decorator(fn: InterpreterFn) -> InterpreterFn:
        _REGISTRY[name] = fn
        return fn
    return decorator


def register_validator(name: str) -> Callable[[ValidatorFn], ValidatorFn]:
    """Decorator that registers a validation function for a named interpreter.

    A validator has signature ``(edge_data: dict) -> None`` and should raise
    ``ValueError`` when the edge data is invalid.  Registering a validator is
    optional; interpreters without one skip validation silently.
    """
    def decorator(fn: ValidatorFn) -> ValidatorFn:
        _VALIDATORS[name] = fn
        return fn
    return decorator


def resolve(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    """Dispatch *edge_data* to its registered interpreter.

    The interpreter is selected via ``edge_data["interpreter"]``.  Raises
    ``KeyError`` for unknown interpreter names.
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


def validate_edge(edge_data: dict) -> None:
    """Run the registered validator for this edge's interpreter, if any.

    Silently does nothing for edges with no ``interpreter`` key or for
    interpreters that have no registered validator.  Raises ``ValueError``
    when the validator finds a problem.
    """
    name = edge_data.get("interpreter")
    if name is None:
        return
    validator = _VALIDATORS.get(name)
    if validator is not None:
        validator(edge_data)
