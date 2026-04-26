# `bw_eotw` Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-26

First release.

### Added

- `RichEdgesBackend` — an alternate Brightway SQLite backend where edges carry an `interpreter` key and are expanded at processing time rather than stored as raw matrix values
- `RichNode` and `RichEdge` / `RichEdges` classes with notebook-friendly `__repr__` and `_repr_html_` display
- Interpreter registry: `@register`, `resolve`, `normalize_edge`, and `validate_edge`
- `Interpreter` base class enforcing the same-database invariant and providing default `normalize` / `validate` hooks
- Five built-in interpreters:
  - `singlevalue` — drop-in replacement for a plain bw2data exchange
  - `loss` — expands one edge into a main flow and a proportional loss component
  - `provider_mix` — splits a single demand across multiple providers by share
  - `temporal` — selects a value from a year-keyed dict using `config["year"]`
  - `temporal_scenario` — selects a value from a scenario × year nested dict
- `set_config(db_name, config)` (also `db.set_config(config)`) for database-level configuration with automatic processed-file cache invalidation; works as both a plain call and a context manager
- `requires_config` flag on interpreters that cannot run without an active config
