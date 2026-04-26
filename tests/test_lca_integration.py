"""Integration tests that run full LCAs through bw2calc.

These tests mirror the notebook patterns and catch issues that unit tests
cannot — in particular, bugs that only appear when processing a database
multiple times with different configs in the same session.
"""

import pytest
import bw2calc
import bw2data
from bw2data.database import Database
from bw2data.tests import bw2test

import bw_eotw  # noqa: F401


def _build_lca_fixture():
    """Set up a minimal two-database LCA system.

    Returns (demo_db, widget_node, coal_node).

    Structure:
      biosphere  — CO2 emission node
      background — coal provider: 1 kWh → 0.82 kg CO2
      demo       — widget node with a temporal edge to coal
      GWP method — CO2 factor = 1 kg CO2-eq / kg
    """
    # biosphere
    bio = Database("biosphere")
    bio.register()
    co2 = bio.new_node(code="co2", name="CO2", unit="kg", type="emission")
    co2.save()
    co2.new_edge(input=co2, type="production", amount=1.0).save()

    # characterisation method
    gwp = bw2data.Method(("GWP",))
    gwp.register()
    gwp.write([(co2.key, 1.0)])

    # background
    bg = Database("background")
    bg.register()
    coal = bg.new_node(code="coal", name="Coal power", unit="kWh", type="process")
    coal.save()
    coal.new_edge(input=coal, type="production", amount=1.0).save()
    coal.new_edge(input=co2, type="biosphere", amount=0.82).save()

    # demo (eotw)
    demo = Database("demo", backend="eotw")
    demo.register()
    widget = demo.new_node(code="widget", name="Widget", unit="unit", type="process")
    widget.save()
    widget.new_edge(input=widget, type="production", amount=1.0).save()

    return demo, widget, coal


def _run_lca(widget):
    fu, data_objs, _ = bw2data.prepare_lca_inputs(
        {widget: 1.0}, method=("GWP",), remapping=False
    )
    lca = bw2calc.LCA(demand=fu, data_objs=data_objs)
    lca.lci()
    lca.lcia()
    return lca.score


# ---------------------------------------------------------------------------
# Temporal interpreter — successive set_config context managers
# ---------------------------------------------------------------------------


@bw2test
def test_temporal_set_config_loop_produces_correct_scores():
    """Iterating over years with set_config as a context manager must give the
    correct GWP for each year without corrupting subsequent iterations.

    This reproduces the notebook section-2 failure where the second LCA call
    yielded a non-square technosphere matrix.
    """
    demo, widget, coal = _build_lca_fixture()

    widget.new_edge(
        input=coal,
        type="technosphere",
        interpreter="temporal",
        temporal_values={2020: 1.20, 2025: 1.00, 2030: 0.85},
        default_year=2025,
    ).save()

    expected = {2020: 1.20 * 0.82, 2025: 1.00 * 0.82, 2030: 0.85 * 0.82}

    for year, exp in expected.items():
        with demo.set_config({"year": year}):
            score = _run_lca(widget)
        assert score == pytest.approx(exp, rel=1e-4), f"year={year}: got {score}, expected {exp}"


@bw2test
def test_temporal_default_year_used_when_no_config():
    """After all context managers exit, a bare LCA call should use default_year."""
    demo, widget, coal = _build_lca_fixture()

    widget.new_edge(
        input=coal,
        type="technosphere",
        interpreter="temporal",
        temporal_values={2020: 1.20, 2025: 1.00, 2030: 0.85},
        default_year=2025,
    ).save()

    with demo.set_config({"year": 2020}):
        pass  # just exercise the context manager; don't run LCA inside

    score = _run_lca(widget)
    assert score == pytest.approx(1.00 * 0.82, rel=1e-4)


@bw2test
def test_temporal_loop_after_prior_singlevalue_section():
    """Reproduce the exact notebook sequence: a singlevalue LCA runs first
    (creating demo.zip on disk), then fresh_demo() re-creates the database,
    and the temporal loop must still give correct scores for every year.

    Database.delete() does NOT remove processed zip files, so demo.zip from
    the first section remains on disk when the temporal section runs.
    """
    bio = Database("biosphere")
    bio.register()
    co2 = bio.new_node(code="co2", name="CO2", unit="kg", type="emission")
    co2.save()
    co2.new_edge(input=co2, type="production", amount=1.0).save()

    gwp = bw2data.Method(("GWP",))
    gwp.register()
    gwp.write([(co2.key, 1.0)])

    bg = Database("background")
    bg.register()
    coal = bg.new_node(code="coal", name="Coal power", unit="kWh", type="process")
    coal.save()
    coal.new_edge(input=coal, type="production", amount=1.0).save()
    coal.new_edge(input=co2, type="biosphere", amount=0.82).save()

    # ── section 1: singlevalue — creates demo.zip on disk ────────────────────
    demo = Database("demo", backend="eotw")
    demo.register()
    widget = demo.new_node(code="widget", name="Widget", unit="unit", type="process")
    widget.save()
    widget.new_edge(input=widget, type="production", amount=1.0).save()
    widget.new_edge(input=coal, type="technosphere", interpreter="singlevalue", amount=1.0).save()
    _run_lca(widget)  # triggers process() → writes demo.zip

    demo_zip = demo.filepath_processed()
    assert demo_zip.exists(), "demo.zip must exist after singlevalue section"

    # ── section 2: fresh_demo — delete+re-create, add temporal edge ──────────
    del bw2data.databases["demo"]
    # demo.zip is still on disk (delete() doesn't remove processed files)
    assert demo_zip.exists(), "demo.zip must still exist after del databases['demo']"

    demo = Database("demo", backend="eotw")
    demo.register()
    widget = demo.new_node(code="widget", name="Widget", unit="unit", type="process")
    widget.save()
    widget.new_edge(input=widget, type="production", amount=1.0).save()
    widget.new_edge(
        input=coal,
        type="technosphere",
        interpreter="temporal",
        temporal_values={2020: 1.20, 2025: 1.00, 2030: 0.85},
        default_year=2025,
    ).save()

    expected = {2020: 1.20 * 0.82, 2025: 1.00 * 0.82, 2030: 0.85 * 0.82}

    for year, exp in expected.items():
        with demo.set_config({"year": year}):
            score = _run_lca(widget)
        assert score == pytest.approx(exp, rel=1e-4), f"year={year}: got {score}, expected {exp}"
