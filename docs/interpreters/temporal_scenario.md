# Temporal-scenario interpreter

**Name:** `"temporal_scenario"`

Combines strict scenario selection with per-year value lookup.  First the active scenario is chosen (strict — raises if absent or unknown), then a year is selected within that scenario using the same fallback logic as the [`temporal`](temporal.md) interpreter.

## Edge data format

`scenario_temporal_values` is a two-level dict: outer keys are scenario names, inner keys are integer years.  Leaf values are either plain numbers or uncertainty dicts.  `default_year` is optional:

```python
{
    "interpreter": "temporal_scenario",
    "input": ("db", "some_code"),
    "output": ("db", "other_code"),
    "type": "technosphere",
    "scenario_temporal_values": {
        "baseline": {
            2020: 1.00,
            2030: 0.85,
        },
        "optimistic": {
            2020: 0.80,
            2030: {"amount": 0.60, "uncertainty_type": 2, "scale": 0.05},
        },
    },
    "default_year": 2020,   # optional
}
```

## Config

| Key | Type | Description |
|---|---|---|
| `scenario` | `str` | **Required.** Must match a key in `scenario_temporal_values`. |
| `year` | `int` | Optional.  Falls back to `default_year` if absent or not found in the scenario. |

## Selection logic

**Scenario (strict):**

1. `config["scenario"]` must be present — `KeyError` otherwise.
2. The value must be a key in `scenario_temporal_values` — `KeyError` otherwise.

**Year within the selected scenario:**

1. If `config["year"]` is present and is a key in the scenario's year dict, that value is used.
2. Otherwise, if `edge_data["default_year"]` is present and is a key in the scenario's year dict, that value is used.
3. Otherwise a `KeyError` is raised, listing what was tried and the available years.

```python
# baseline scenario, year 2030 → 0.85
db.process(config={"scenario": "baseline", "year": 2030})

# optimistic scenario, year 2025 → not found, falls back to default_year=2020 → 0.80
db.process(config={"scenario": "optimistic", "year": 2025})

# missing scenario key → KeyError
db.process(config={"year": 2020})

# unknown scenario → KeyError
db.process(config={"scenario": "pessimistic", "year": 2020})
```

## Output

One `MatrixEntry`.  Uncertainty fields are taken from the selected value dict when present.

## Validation

The validator (`validate_temporal_scenario`) checks:

- `scenario_temporal_values` is present and non-empty.
- Each scenario has at least one year entry.
- If `default_year` is set, it must be present in **every** scenario's year dict (so the fallback can never silently fail for any scenario).

```python
# This raises — "optimistic" is missing 2020
validate_edge({
    "interpreter": "temporal_scenario",
    "scenario_temporal_values": {
        "baseline":   {2020: 1.0, 2030: 0.9},
        "optimistic": {2030: 0.7},
    },
    "default_year": 2020,
})
```
