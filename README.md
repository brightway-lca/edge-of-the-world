# edge-of-the-world (`bw_eotw`)

[![PyPI](https://img.shields.io/pypi/v/bw_eotw.svg)][pypi status]
[![Python Version](https://img.shields.io/pypi/pyversions/bw_eotw)][pypi status]
[![License](https://img.shields.io/pypi/l/bw_eotw)][license]
[![Tests](https://github.com/brightway-lca/edge-of-the-world/actions/workflows/python-test.yml/badge.svg)][tests]

[pypi status]: https://pypi.org/project/bw_eotw/
[license]: https://github.com/brightway-lca/edge-of-the-world/blob/main/LICENSE
[tests]: https://github.com/brightway-lca/edge-of-the-world/actions?workflow=Tests

An alternate [Brightway](https://brightway.dev) backend with richer edge descriptions. Instead of each exchange mapping directly to one matrix cell, edges carry an `interpreter` key that controls how they expand at processing time — one edge can become multiple matrix entries, or its value can be selected from a config-driven lookup table.

## Installation

```console
pip install bw_eotw
```

Requires Python ≥ 3.9 and `bw2data >= 4.0`.

## Quickstart

```python
import bw2data
import bw_eotw  # registers the "eotw" backend on import

bw2data.projects.set_current("my-project")

db = bw2data.Database("my-db", backend="eotw")
db.register()

node = db.new_node(name="electricity", type="process", unit="kWh")
node.save()

# A plain edge — identical to a standard bw2data exchange
node.new_edge(
    input=other_node,
    type="technosphere",
    interpreter="singlevalue",
    amount=2.5,
).save()

db.process()
```

## Core concepts

### `RichEdgesBackend`

`RichEdgesBackend` is a drop-in replacement for Brightway's `SQLiteBackend`. The only behavioural difference is that edges with an `interpreter` key are dispatched to the registered interpreter during `process()`. Edges without that key are passed through unchanged, so existing datasets need no migration.

Create a database with this backend:

```python
db = bw2data.Database("my-db", backend="eotw")
```

`write()` is disabled — use `db.new_node()` / `node.new_edge()` to build the database incrementally.

### Interpreters

An interpreter is a callable registered under a name. When `process()` encounters an edge with `"interpreter": "name"`, it calls the interpreter with the edge data and the active config, and writes whatever `MatrixEntry` objects the interpreter yields.

#### Built-in interpreters

| Name | What it does |
|---|---|
| `singlevalue` | Single matrix cell; identical to a plain bw2data exchange |
| `loss` | Main flow + proportional loss component in the same cell |
| `provider_mix` | Splits demand across multiple providers by fractional share |
| `temporal` | Picks a value from a year-keyed dict; year comes from config |
| `temporal_scenario` | Picks a value from a scenario × year nested dict |

##### `singlevalue`

```python
node.new_edge(
    input=other_node, type="technosphere",
    interpreter="singlevalue", amount=1.5,
).save()
```

##### `loss`

```python
node.new_edge(
    input=other_node, type="technosphere",
    interpreter="loss",
    amount=1.0,       # main flow
    loss_factor=0.05, # 5 % loss; must be a plain number in [0, 1]
).save()
```

Yields two entries into the same matrix cell: `amount` and `amount * loss_factor`.

##### `provider_mix`

```python
node.new_edge(
    input=dummy_node, type="technosphere",
    interpreter="provider_mix",
    product_name="electricity",
    amount=2.0,
    mix=[
        {"input": provider_a.id, "share": 0.60},
        {"input": provider_b.id, "share": 0.40},
    ],
).save()
```

Shares must sum to 1. All `input` nodes must be in the same database. Pass `Node` instances or integer IDs — `normalize_edge` converts them automatically on save.

##### `temporal`

```python
node.new_edge(
    input=other_node, type="technosphere",
    interpreter="temporal",
    temporal_values={2010: 0.3, 2020: 0.4, 2030: 0.6},
    default_year=2020,  # used when config has no "year" key
).save()
```

Year lookup order: `config["year"]` → `edge["default_year"]` → `KeyError`.

##### `temporal_scenario`

```python
node.new_edge(
    input=other_node, type="technosphere",
    interpreter="temporal_scenario",
    scenario_temporal_values={
        "baseline":   {2020: 1.00, 2030: 0.85},
        "optimistic": {2020: 0.80, 2030: 0.60},
    },
    default_year=2020,
).save()
```

`config["scenario"]` is required; `config["year"]` falls back to `default_year`.

### Config and cache invalidation

Some interpreters (e.g. `temporal`, `temporal_scenario`) need a config dict at processing time. Set it before calling `process()` or `prepare_lca_inputs()`:

```python
# Plain call — stays active until changed
db.set_config({"year": 2030})
db.process()

# Context manager — restores previous config on exit
with db.set_config({"year": 2030, "scenario": "optimistic"}):
    fu, data_objs, remapping = bw2data.prepare_lca_inputs(...)
```

`set_config` stores the config in database metadata and appends a short hash to the processed filename, so different configs produce different cached datapackages. Stale variants are cleaned up automatically when the database is reprocessed.

To clear the active config:

```python
db.set_config(None)
```

### Custom interpreters

Subclass `Interpreter` and decorate with `@register`:

```python
from bw_eotw import Interpreter, register
from bw_eotw.matrix_entry import MatrixEntry

@register("my_interpreter")
class MyInterpreter(Interpreter):
    def __call__(self, edge_data, config):
        # yield one or more MatrixEntry objects
        yield MatrixEntry.from_edge_value(edge_data, edge_data)

    def iter_node_ids(self, edge_data):
        yield from ()  # yield any extra integer node IDs embedded in edge_data
```

Override `normalize` to convert bw2data `Node` instances to integer IDs before save, `validate` to add structural checks (call `super().validate()` to keep the same-database invariant), and `repr_parts` / `html_rows` for notebook display.

Set `requires_config = True` if the interpreter cannot run without an active config — `resolve()` will raise `ValueError` early rather than failing mid-process.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Distributed under the [MIT license](LICENSE).
