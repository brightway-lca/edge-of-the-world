# Provider mix interpreter

**Name:** `"provider_mix"`

Expands a single product demand into one matrix entry per provider.  This lets you say "I need 2 kWh of electricity" and then specify exactly which generating technologies supply it, with what shares.

## Edge data format

```python
{
    "interpreter": "provider_mix",
    "input": ("grid", "wind"),       # any valid node — used by bw2data for storage
    "output": ("my_db", "factory"),
    "type": "technosphere",
    "product_name": "electricity",   # what is being consumed
    "amount": 2.0,                   # total amount demanded
    "mix": [
        {"input": ("grid", "wind"),  "share": 0.40},
        {"input": ("grid", "solar"), "share": 0.35},
        {"input": ("grid", "gas"),   "share": 0.25},
    ],
}
```

Each entry in `mix` must have:

| Key | Type | Description |
|---|---|---|
| `input` | `(database, code)` | The provider node |
| `share` | `float` | Fraction of the total amount supplied by this provider, in [0, 1] |

## Config

The config is ignored.

## Output

One `MatrixEntry` per provider, each with:

- `row` = the provider node's integer ID (resolved via `bw2data.get_id`)
- `col` = the consuming process's integer ID (from the edge's `col`)
- `amount` = `amount × share`

## Validation

When the edge is saved:

- `product_name` must be present and non-empty.
- `mix` must be non-empty.
- Every provider must have both `input` and `share`.
- Each `share` must be in [0, 1].
- All shares must sum to 1 (checked with `math.isclose`, `abs_tol=1e-9` to tolerate floating-point rounding).

```python
# shares not summing to 1 → ValueError on edge.save()
"mix": [{"input": ..., "share": 0.4}, {"input": ..., "share": 0.4}]

# floating-point sums that are effectively 1 are accepted
"mix": [{"input": ..., "share": 0.1},
        {"input": ..., "share": 0.2},
        {"input": ..., "share": 0.7}]   # 0.1 + 0.2 + 0.7 ≈ 1.0 ✓
```

!!! note "The `input` field"
    bw2data requires every exchange to reference a valid node as its `input`.
    For `provider_mix` edges, set `input` to any one of the provider nodes
    (the first provider is a natural choice).  The field is used only for
    storage; the actual matrix rows come from each entry in `mix`.
