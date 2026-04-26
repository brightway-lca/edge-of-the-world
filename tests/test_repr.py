"""Tests for RichEdge.__repr__ and RichEdge._repr_html_."""

from bw2data.database import Database
from bw2data.tests import bw2test

import bw_eotw  # noqa: F401


def _db_with_nodes():
    db = Database("test", backend="eotw")
    db.register()
    inp = db.new_node(code="a", name="Input node", type="process")
    inp.save()
    out = db.new_node(code="b", name="Output node", type="process")
    out.save()
    return inp, out


# ── __repr__ ─────────────────────────────────────────────────────────────────


class TestRepr:
    @bw2test
    def test_no_interpreter(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, amount=1.5, type="technosphere")
        edge.save()
        r = repr(edge)
        assert r.startswith("RichEdge(")
        assert "interpreter" not in r
        assert "amount=1.5" in r

    @bw2test
    def test_singlevalue(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, interpreter="singlevalue", amount=2.0, type="technosphere")
        edge.save()
        r = repr(edge)
        assert "interpreter='singlevalue'" in r
        assert "amount=2.0" in r

    @bw2test
    def test_singlevalue_flip(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, interpreter="singlevalue", amount=1.0, flip=True, type="technosphere")
        edge.save()
        assert "flip=True" in repr(edge)

    @bw2test
    def test_singlevalue_no_flip_shown(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, interpreter="singlevalue", amount=1.0, flip=False, type="technosphere")
        edge.save()
        assert "flip" not in repr(edge)

    @bw2test
    def test_temporal(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="temporal",
            temporal_values={2010: 0.3, 2020: 0.4, 2030: 0.6},
            type="technosphere",
        )
        edge.save()
        r = repr(edge)
        assert "interpreter='temporal'" in r
        assert "years=[2010, 2020, 2030]" in r
        assert "default_year" not in r

    @bw2test
    def test_temporal_with_default_year(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="temporal",
            temporal_values={2010: 0.3, 2020: 0.4},
            default_year=2020,
            type="technosphere",
        )
        edge.save()
        assert "default_year=2020" in repr(edge)

    @bw2test
    def test_scenario(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="scenario",
            scenario_values={"baseline": 1.0, "optimistic": 0.7, "pessimistic": 1.3},
            type="technosphere",
        )
        edge.save()
        r = repr(edge)
        assert "interpreter='scenario'" in r
        assert "scenarios=['baseline', 'optimistic', 'pessimistic']" in r

    @bw2test
    def test_provider_mix(self):
        inp, out = _db_with_nodes()
        extra = Database("test").new_node(code="c", name="Extra node", type="process")
        extra.save()
        edge = out.new_edge(
            input=inp,
            interpreter="provider_mix",
            product_name="electricity",
            amount=2.0,
            mix=[{"input": inp.id, "share": 0.6}, {"input": extra.id, "share": 0.4}],
            type="technosphere",
        )
        edge.save()
        r = repr(edge)
        assert "interpreter='provider_mix'" in r
        assert "product='electricity'" in r
        assert "n_providers=2" in r

    @bw2test
    def test_temporal_scenario(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="temporal_scenario",
            scenario_temporal_values={
                "baseline":   {2020: 1.0, 2030: 0.85},
                "optimistic": {2020: 0.8, 2030: 0.60},
            },
            type="technosphere",
        )
        edge.save()
        r = repr(edge)
        assert "interpreter='temporal_scenario'" in r
        assert "scenarios=['baseline', 'optimistic']" in r
        assert "years=[2020, 2030]" in r

    @bw2test
    def test_loss(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, interpreter="loss", amount=1.0, loss_factor=0.05, type="technosphere")
        edge.save()
        r = repr(edge)
        assert "interpreter='loss'" in r
        assert "amount=1.0" in r
        assert "loss_factor=0.05" in r

    @bw2test
    def test_unknown_interpreter(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, interpreter="custom", amount=1.0, type="technosphere")
        edge.save()
        assert "interpreter='custom'" in repr(edge)

    @bw2test
    def test_input_output_show_node_repr(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, interpreter="singlevalue", amount=1.0, type="technosphere")
        edge.save()
        r = repr(edge)
        assert repr(inp) in r
        assert repr(out) in r


# ── _repr_html_ ──────────────────────────────────────────────────────────────


class TestReprHtml:
    @bw2test
    def test_returns_string(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, amount=1.0, type="technosphere")
        edge.save()
        assert isinstance(edge._repr_html_(), str)

    @bw2test
    def test_no_interpreter_shows_amount(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, amount=3.14, type="technosphere")
        edge.save()
        h = edge._repr_html_()
        assert "3.14" in h
        assert "input" in h
        assert "output" in h

    @bw2test
    def test_singlevalue_color_in_header(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, interpreter="singlevalue", amount=1.0, type="technosphere")
        edge.save()
        h = edge._repr_html_()
        assert "singlevalue" in h
        assert "#6c757d" in h

    @bw2test
    def test_temporal_lists_years(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="temporal",
            temporal_values={2010: 0.3, 2020: 0.4},
            type="technosphere",
        )
        edge.save()
        h = edge._repr_html_()
        assert "2010" in h
        assert "2020" in h
        assert "0.3" in h
        assert "#0d6efd" in h  # blue

    @bw2test
    def test_temporal_default_year_shown(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="temporal",
            temporal_values={2020: 1.0},
            default_year=2020,
            type="technosphere",
        )
        edge.save()
        assert "default_year" in edge._repr_html_()

    @bw2test
    def test_scenario_lists_scenarios(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="scenario",
            scenario_values={"baseline": 1.0, "optimistic": 0.7},
            type="technosphere",
        )
        edge.save()
        h = edge._repr_html_()
        assert "baseline" in h
        assert "optimistic" in h
        assert "#198754" in h  # green

    @bw2test
    def test_uncertainty_dict_shown(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="scenario",
            scenario_values={"hi": {"amount": 0.5, "uncertainty_type": 2, "scale": 0.1}},
            type="technosphere",
        )
        edge.save()
        assert "ut=2" in edge._repr_html_()

    @bw2test
    def test_provider_mix_shows_shares(self):
        inp, out = _db_with_nodes()
        extra = Database("test").new_node(code="c", name="Extra node", type="process")
        extra.save()
        edge = out.new_edge(
            input=inp,
            interpreter="provider_mix",
            product_name="heat",
            amount=1.0,
            mix=[{"input": inp.id, "share": 0.75}, {"input": extra.id, "share": 0.25}],
            type="technosphere",
        )
        edge.save()
        h = edge._repr_html_()
        assert "heat" in h
        assert "75.0%" in h
        assert "25.0%" in h
        assert "#fd7e14" in h  # orange

    @bw2test
    def test_temporal_scenario_grid(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="temporal_scenario",
            scenario_temporal_values={
                "baseline":   {2020: 1.0, 2030: 0.85},
                "optimistic": {2020: 0.8, 2030: 0.60},
            },
            type="technosphere",
        )
        edge.save()
        h = edge._repr_html_()
        assert "baseline" in h
        assert "optimistic" in h
        assert "2020" in h
        assert "2030" in h
        assert "0.85" in h
        assert "#6f42c1" in h  # purple

    @bw2test
    def test_temporal_scenario_missing_cell_shows_dash(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(
            input=inp,
            interpreter="temporal_scenario",
            scenario_temporal_values={
                "a": {2020: 1.0},
                "b": {2030: 0.5},
            },
            type="technosphere",
        )
        edge.save()
        assert "—" in edge._repr_html_()

    @bw2test
    def test_loss_shows_loss_factor(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, interpreter="loss", amount=1.0, loss_factor=0.05, type="technosphere")
        edge.save()
        h = edge._repr_html_()
        assert "loss_factor" in h
        assert "0.05" in h
        assert "#dc3545" in h  # red

    @bw2test
    def test_input_output_node_repr_in_html(self):
        inp, out = _db_with_nodes()
        edge = out.new_edge(input=inp, interpreter="singlevalue", amount=1.0, type="technosphere")
        edge.save()
        h = edge._repr_html_()
        assert repr(inp) in h
        assert repr(out) in h
