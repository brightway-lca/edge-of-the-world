# edge-of-the-world

**edge-of-the-world** (`bw_eotw`) is an alternate database backend for [Brightway](https://docs.brightway.dev) that allows edges (exchanges) to carry richer descriptions than a single `(row, col, amount)` matrix cell.

In standard Brightway, every exchange maps exactly to one matrix entry.  `bw_eotw` lifts that constraint: a single edge can resolve to **multiple matrix entries**, and the values can be **selected dynamically** based on a calculation configuration such as the target year.

## When to use it

- You need **time-differentiated** supply chains (different amounts for 2020 vs 2030).
- A single exchange involves **process losses** that must be tracked separately.
- You want a clean extension point for custom edge semantics without forking bw2data.

## Installation

```console
pip install bw_eotw
```

## Quick start

Register the backend by importing the package, then create a database as usual:

```python
import bw2data as bd
import bw_eotw  # registers the "eotw" backend

db = bd.Database("my_db", backend="eotw")
```

### Writing a temporal edge

Edges are plain dicts with an extra `interpreter` key.  The `temporal` interpreter picks the right value for a given year:

```python
node["exchanges"].append({
    "input": ("other_db", "some_process"),
    "output": ("my_db", "my_process"),
    "type": "technosphere",
    "interpreter": "temporal",
    "temporal_values": {
        2020: 0.80,
        2030: 0.65,
    },
})
```

Process with a year in the config:

```python
db.process(config={"year": 2030})
```

### Writing a loss edge

```python
node["exchanges"].append({
    "input": ("other_db", "feedstock"),
    "output": ("my_db", "my_process"),
    "type": "technosphere",
    "interpreter": "loss",
    "amount": 1.0,
    "loss_factor": 0.05,   # 5 % loss — must be in [0, 1]
})
```

## How it works

1. Each edge can carry an `interpreter` key naming a registered function.
2. When `process(config=...)` is called, the backend iterates all exchanges and passes those with an `interpreter` key to the matching function.
3. The function receives the full edge data dict and the config dict, and yields one or more [`MatrixEntry`](interpreters/index.md) objects.
4. Standard edges (no `interpreter` key) pass through unchanged — **existing databases require no migration**.
