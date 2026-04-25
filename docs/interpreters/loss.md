# Loss interpreter

**Name:** `"loss"`

Expands a single edge into two matrix entries: the main flow and a proportional loss component.  Both entries share the same `(row, col)` pair and are summed by bw_processing, giving an effective gross input of `amount × (1 + loss_factor)`.

## Edge data format

```python
{
    "interpreter": "loss",
    "input": ("db", "feedstock"),
    "output": ("db", "my_process"),
    "type": "technosphere",
    "amount": 1.0,
    "loss_factor": 0.05,   # 5 % loss
}
```

`loss_factor` may also be an uncertainty dict if the loss fraction itself is uncertain:

```python
{
    "interpreter": "loss",
    "amount": 1.0,
    "loss_factor": {
        "amount": 0.05,
        "uncertainty_type": 2,
        "scale": 0.01,
    },
}
```

## Config

The config is ignored.

## Output

Two `MatrixEntry` objects with the same `(row, col)`:

| Entry | Amount | Uncertainty |
|---|---|---|
| Main flow | `amount` | From the edge's own uncertainty fields |
| Loss flow | `amount × loss_factor` | From `loss_factor`'s uncertainty fields, scaled by `amount` |

When `loss_factor` is an uncertainty dict, its unit-bearing fields (`loc`, `scale`, `minimum`, `maximum`) are multiplied by `amount` so that the loss entry's distribution is in the same units as the amount.  The dimensionless `shape` parameter is not scaled.

## Validation

`loss_factor` is validated when the edge is saved:

- The field must be present.
- Its central value (`amount` if a dict, otherwise the number itself) must satisfy `0 ≤ loss_factor ≤ 1`.

```python
edge["loss_factor"] = 1.5   # raises ValueError on edge.save()
edge["loss_factor"] = -0.1  # raises ValueError on edge.save()
edge["loss_factor"] = 0.0   # valid
edge["loss_factor"] = 1.0   # valid
```
