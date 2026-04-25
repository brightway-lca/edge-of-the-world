# Temporal interpreter

**Name:** `"temporal"`

Selects an amount from a year-keyed lookup table.  An optional per-edge `default_year` is used as a fallback when the config year is absent or not found.

## Edge data format

`temporal_values` is a dict keyed by **integer year**.  Each value is either a plain number or a bw2data-style uncertainty dict.  `default_year` is optional:

```python
{
    "interpreter": "temporal",
    "input": ("db", "some_code"),
    "output": ("db", "other_code"),
    "type": "technosphere",
    "temporal_values": {
        2010: 0.30,
        2020: {"amount": 0.40, "uncertainty_type": 2, "scale": 0.04},
        2030: 0.60,
    },
    "default_year": 2020,   # optional
}
```

## Config

| Key | Type | Description |
|---|---|---|
| `year` | `int` | The target year.  Optional; falls back to `default_year` if absent or not found. |

## Year selection logic

1. If `config["year"]` is present **and** is a key in `temporal_values`, that value is used.
2. Otherwise, if `edge_data["default_year"]` is present and is a key in `temporal_values`, that value is used.
3. Otherwise a `KeyError` is raised, listing what was tried and the available years.

```python
# year=2030 → uses 0.60
db.process(config={"year": 2030})

# year=2025 → not in table, falls back to default_year=2020 → uses 0.40
db.process(config={"year": 2025})

# no year, default_year=2020 in edge data → uses 0.40
db.process(config={})

# no year, no default_year → KeyError
db.process(config={})
```

## Output

One `MatrixEntry`.  Uncertainty fields are taken from the selected value dict when present, or left at their defaults (no uncertainty) for plain numbers.

## Validation

No validator is registered for `temporal`.  The `KeyError` raised during `process()` when years are missing serves as the runtime guard.
