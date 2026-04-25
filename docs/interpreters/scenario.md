# Scenario interpreter

**Name:** `"scenario"`

Selects a value by scenario name.  Unlike the [temporal interpreter](temporal.md), there is no fallback: if the requested scenario is not present in the edge data, a `KeyError` is raised immediately.

## Edge data format

`scenario_values` is a dict keyed by **string scenario name**.  Each value is either a plain number or a bw2data-style uncertainty dict:

```python
{
    "interpreter": "scenario",
    "input": ("db", "some_code"),
    "output": ("db", "other_code"),
    "type": "technosphere",
    "scenario_values": {
        "baseline":    1.00,
        "optimistic":  {"amount": 0.70, "uncertainty_type": 2, "scale": 0.05},
        "pessimistic": 1.30,
    },
}
```

## Config

| Key | Type | Description |
|---|---|---|
| `scenario` | `str` | **Required.** The scenario name to select. |

## Scenario selection logic

1. If `"scenario"` is absent from `config`, a `KeyError` is raised listing the available scenarios.
2. If `config["scenario"]` is not a key in `scenario_values`, a `KeyError` is raised listing the available scenarios.
3. Otherwise, the matching value is used.

```python
db.process(config={"scenario": "optimistic"})   # uses 0.70
db.process(config={"scenario": "missing"})       # KeyError — lists available names
db.process(config={})                            # KeyError — 'scenario' key required
```

## Output

One `MatrixEntry`.  Uncertainty fields are taken from the selected value dict when present, or left at their defaults for plain numbers.

## Validation

`scenario_values` is validated when the edge is saved:

- The field must be present.
- It must be a non-empty dict.

```python
edge["scenario_values"] = {}    # raises ValueError on edge.save()
del edge["scenario_values"]     # raises ValueError on edge.save()
```

The scenario name itself is **not** validated at save time — only at `process()` — because valid scenario names are not known until a config is provided.
