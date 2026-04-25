# Standard interpreter

**Name:** `"standard"`

The standard interpreter replicates the behaviour of a plain bw2data exchange.  It yields exactly one `MatrixEntry` with the edge's `amount` and uncertainty fields, and ignores the config.

## When to use it

You do not need to set `"interpreter": "standard"` explicitly — edges without an `interpreter` key are passed through unchanged by the backend and behave identically.  The `standard` interpreter exists so that custom code that always calls `resolve()` has a safe default to dispatch to.

## Edge data format

```python
{
    # no "interpreter" key needed — or set "interpreter": "standard"
    "input": ("db", "some_code"),
    "output": ("db", "other_code"),
    "type": "technosphere",
    "amount": 0.5,
    # optional uncertainty fields:
    "uncertainty_type": 2,
    "scale": 0.05,
}
```

## Config

The config is ignored.

## Output

One `MatrixEntry` with all uncertainty fields taken directly from the edge data.
