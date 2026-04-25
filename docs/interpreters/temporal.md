# Temporal interpreter

**Name:** `"temporal"`

Selects an amount from a year-keyed lookup table, falling back to the year 2020 when the requested year is not present.

## Edge data format

`temporal_values` is a dict keyed by **integer year**.  Each value is either a plain number or a bw2data-style uncertainty dict:

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
}
```

## Config

| Key | Type | Description |
|---|---|---|
| `year` | `int` | The target year.  Defaults to `2020` if absent. |

## Year selection logic

1. If `config["year"]` is a key in `temporal_values`, that value is used.
2. Otherwise, the value for year `2020` is used as a fallback.
3. If neither the requested year nor `2020` is present, a `KeyError` is raised with a message listing the available years.

```python
# year=2030 → uses 0.60
db.process(config={"year": 2030})

# year=2025 → not in table, falls back to 2020 → uses 0.40
db.process(config={"year": 2025})

# no year → defaults to 2020 → uses 0.40
db.process(config={})
```

## Output

One `MatrixEntry`.  Uncertainty fields are taken from the selected value dict when present, or left at their defaults (no uncertainty) for plain numbers.

## Validation

No validator is registered for `temporal`.  The `KeyError` raised during `process()` when years are missing serves as the runtime guard.
