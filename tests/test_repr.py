"""Tests for RichEdge.__repr__ and RichEdge._repr_html_."""

from bw_eotw.edge_classes import RichEdge


def make_edge(**kwargs) -> RichEdge:
    """Build a RichEdge from raw data without touching the database."""
    return RichEdge(**kwargs)


# ── __repr__ ─────────────────────────────────────────────────────────────────


class TestRepr:
    def test_no_interpreter(self):
        e = make_edge(input=("db", "abc"), output=("db", "xyz"), amount=1.5)
        r = repr(e)
        assert r.startswith("RichEdge(")
        assert "interpreter" not in r
        assert "amount=1.5" in r

    def test_standard(self):
        e = make_edge(interpreter="standard", input=("db", "a"), output=("db", "b"), amount=2.0)
        r = repr(e)
        assert "interpreter='standard'" in r
        assert "amount=2.0" in r

    def test_standard_flip(self):
        e = make_edge(interpreter="standard", input=("db", "a"), output=("db", "b"), amount=1.0, flip=True)
        assert "flip=True" in repr(e)

    def test_standard_no_flip_shown(self):
        e = make_edge(interpreter="standard", input=("db", "a"), output=("db", "b"), amount=1.0, flip=False)
        assert "flip" not in repr(e)

    def test_temporal(self):
        e = make_edge(
            interpreter="temporal",
            input=("db", "a"), output=("db", "b"),
            temporal_values={2010: 0.3, 2020: 0.4, 2030: 0.6},
        )
        r = repr(e)
        assert "interpreter='temporal'" in r
        assert "years=[2010, 2020, 2030]" in r
        assert "default_year" not in r

    def test_temporal_with_default_year(self):
        e = make_edge(
            interpreter="temporal",
            input=("db", "a"), output=("db", "b"),
            temporal_values={2010: 0.3, 2020: 0.4},
            default_year=2020,
        )
        r = repr(e)
        assert "default_year=2020" in r

    def test_scenario(self):
        e = make_edge(
            interpreter="scenario",
            input=("db", "a"), output=("db", "b"),
            scenario_values={"baseline": 1.0, "optimistic": 0.7, "pessimistic": 1.3},
        )
        r = repr(e)
        assert "interpreter='scenario'" in r
        assert "scenarios=['baseline', 'optimistic', 'pessimistic']" in r

    def test_provider_mix(self):
        e = make_edge(
            interpreter="provider_mix",
            input=("db", "a"), output=("db", "b"),
            product_name="electricity",
            amount=2.0,
            mix=[{"input": 101, "share": 0.6}, {"input": 102, "share": 0.4}],
        )
        r = repr(e)
        assert "interpreter='provider_mix'" in r
        assert "product='electricity'" in r
        assert "n_providers=2" in r

    def test_temporal_scenario(self):
        e = make_edge(
            interpreter="temporal_scenario",
            input=("db", "a"), output=("db", "b"),
            scenario_temporal_values={
                "baseline":   {2020: 1.0, 2030: 0.85},
                "optimistic": {2020: 0.8, 2030: 0.60},
            },
        )
        r = repr(e)
        assert "interpreter='temporal_scenario'" in r
        assert "scenarios=['baseline', 'optimistic']" in r
        assert "years=[2020, 2030]" in r

    def test_loss(self):
        e = make_edge(interpreter="loss", input=("db", "a"), output=("db", "b"), amount=1.0, loss_factor=0.05)
        r = repr(e)
        assert "interpreter='loss'" in r
        assert "amount=1.0" in r
        assert "loss_factor=0.05" in r

    def test_unknown_interpreter(self):
        e = make_edge(interpreter="custom", input=("db", "a"), output=("db", "b"))
        r = repr(e)
        assert "interpreter='custom'" in r


# ── _repr_html_ ──────────────────────────────────────────────────────────────


class TestReprHtml:
    def html(self, **kwargs) -> str:
        return make_edge(**kwargs)._repr_html_()

    def test_returns_string(self):
        h = self.html(input=("db", "a"), output=("db", "b"), amount=1.0)
        assert isinstance(h, str)

    def test_no_interpreter_shows_amount(self):
        h = self.html(input=("db", "a"), output=("db", "b"), amount=3.14)
        assert "3.14" in h
        assert "input" in h
        assert "output" in h

    def test_standard_color_in_header(self):
        h = self.html(interpreter="standard", input=("db", "a"), output=("db", "b"), amount=1.0)
        assert "standard" in h
        assert "#6c757d" in h

    def test_temporal_lists_years(self):
        h = self.html(
            interpreter="temporal",
            input=("db", "a"), output=("db", "b"),
            temporal_values={2010: 0.3, 2020: 0.4},
        )
        assert "2010" in h
        assert "2020" in h
        assert "0.3" in h
        assert "#0d6efd" in h  # blue

    def test_temporal_default_year_shown(self):
        h = self.html(
            interpreter="temporal",
            input=("db", "a"), output=("db", "b"),
            temporal_values={2020: 1.0},
            default_year=2020,
        )
        assert "default_year" in h

    def test_scenario_lists_scenarios(self):
        h = self.html(
            interpreter="scenario",
            input=("db", "a"), output=("db", "b"),
            scenario_values={"baseline": 1.0, "optimistic": 0.7},
        )
        assert "baseline" in h
        assert "optimistic" in h
        assert "#198754" in h  # green

    def test_uncertainty_dict_shown(self):
        h = self.html(
            interpreter="scenario",
            input=("db", "a"), output=("db", "b"),
            scenario_values={"hi": {"amount": 0.5, "uncertainty_type": 2, "scale": 0.1}},
        )
        assert "ut=2" in h

    def test_provider_mix_shows_shares(self):
        h = self.html(
            interpreter="provider_mix",
            input=("db", "a"), output=("db", "b"),
            product_name="heat",
            amount=1.0,
            mix=[{"input": 5, "share": 0.75}, {"input": 6, "share": 0.25}],
        )
        assert "heat" in h
        assert "75.0%" in h
        assert "25.0%" in h
        assert "#fd7e14" in h  # orange

    def test_temporal_scenario_grid(self):
        h = self.html(
            interpreter="temporal_scenario",
            input=("db", "a"), output=("db", "b"),
            scenario_temporal_values={
                "baseline":   {2020: 1.0, 2030: 0.85},
                "optimistic": {2020: 0.8, 2030: 0.60},
            },
        )
        assert "baseline" in h
        assert "optimistic" in h
        assert "2020" in h
        assert "2030" in h
        assert "0.85" in h
        assert "#6f42c1" in h  # purple

    def test_temporal_scenario_missing_cell_shows_dash(self):
        h = self.html(
            interpreter="temporal_scenario",
            input=("db", "a"), output=("db", "b"),
            scenario_temporal_values={
                "a": {2020: 1.0},
                "b": {2030: 0.5},  # no 2020 entry
            },
        )
        assert "—" in h

    def test_loss_shows_loss_factor(self):
        h = self.html(interpreter="loss", input=("db", "a"), output=("db", "b"), amount=1.0, loss_factor=0.05)
        assert "loss_factor" in h
        assert "0.05" in h
        assert "#dc3545" in h  # red

    def test_input_output_tuples_in_html(self):
        h = self.html(
            interpreter="standard",
            input=("mydb", "node1"), output=("mydb", "node2"),
            amount=1.0,
        )
        assert "mydb" in h
        assert "node1" in h
        assert "node2" in h
