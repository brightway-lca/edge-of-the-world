# Interpreters

An **interpreter** is a function that turns one edge's stored data into zero or more [`MatrixEntry`](#matrixentry) objects — the realised values that are written into the sparse matrix during `process()`.

## The interpreter contract

Every interpreter has this signature:

```python
def my_interpreter(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    ...
```

| Argument | Description |
|---|---|
| `edge_data` | The full exchange data dict, including `row`, `col`, `flip`, and any custom keys |
| `config` | The calculation config passed to `db.process(config=...)` — typically contains keys like `"year"` |

The function must `yield` at least zero `MatrixEntry` instances.  Yielding more than one causes multiple entries in the processing array; bw_processing sums those that share the same `(row, col)` pair.

## MatrixEntry

`MatrixEntry` is a frozen dataclass that mirrors the fields expected by bw_processing:

```python
@dataclasses.dataclass(frozen=True)
class MatrixEntry:
    row: int
    col: int
    amount: float
    flip: bool = False
    uncertainty_type: int = 0
    loc: float = nan
    scale: float = nan
    shape: float = nan
    minimum: float = nan
    maximum: float = nan
    negative: bool = False
```

Use `MatrixEntry.from_edge_value(value, edge_data)` to construct one from a value (plain number or uncertainty dict) plus the surrounding edge data that provides `row`, `col`, and `flip`.

## Registering a custom interpreter

Use the `register` decorator from `bw_eotw`:

```python
from collections.abc import Iterator
from bw_eotw import register, MatrixEntry

@register("my_interpreter")
def my_interpreter(edge_data: dict, config: dict) -> Iterator[MatrixEntry]:
    amount = edge_data["amount"] * config.get("scale_factor", 1.0)
    yield MatrixEntry(
        row=edge_data["row"],
        col=edge_data["col"],
        amount=amount,
    )
```

Make sure this module is imported before `process()` is called.  The `bw_eotw` package imports all built-in interpreters automatically.

## Registering a validator

Validators run when a `RichEdge` is saved and catch bad data early:

```python
from bw_eotw import register_validator

@register_validator("my_interpreter")
def validate_my_interpreter(edge_data: dict) -> None:
    if "my_required_key" not in edge_data:
        raise ValueError("my_interpreter edges must have 'my_required_key'")
```

Validators are optional.  Interpreters without a registered validator skip validation silently.

## Built-in interpreters

| Name | Description |
|---|---|
| [`standard`](standard.md) | Single-cell, identical to a plain bw2data exchange |
| [`temporal`](temporal.md) | Selects a value by year with a 2020 fallback |
| [`loss`](loss.md) | Expands into a main flow and a proportional loss component |
| [`scenario`](scenario.md) | Selects a value by scenario name; raises if the scenario is absent |
| [`provider_mix`](provider_mix.md) | Splits a product demand across multiple provider nodes by share |
| [`temporal_scenario`](temporal_scenario.md) | Selects a value by scenario name and then by year |
