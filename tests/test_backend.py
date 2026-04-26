import pytest
from bw2data import databases
from bw2data.database import Database
from bw2data.tests import bw2test

import bw_eotw  # noqa: F401 — registers the backend
from bw_eotw import set_config


def _make_db(name):
    db = Database(name, backend="eotw")
    db.register()
    return db


def _make_node(db, code, name):
    node = db.new_node(code=code, name=name, type="process")
    node.save()
    node.new_edge(input=node, type="production", amount=1.0).save()
    return node


# ---------------------------------------------------------------------------
# Dependents tracking
# ---------------------------------------------------------------------------


@bw2test
def test_same_database_edge_leaves_depends_empty():
    db = _make_db("solo")
    _make_node(db, "X", "node X")
    db.process()
    assert db.metadata.get("depends", []) == []


@bw2test
def test_cross_database_edge_adds_to_depends():
    supplier = Database("supplier")
    supplier.write({("supplier", "A"): {"name": "node A", "type": "process", "exchanges": [
        {"input": ("supplier", "A"), "output": ("supplier", "A"), "amount": 1.0, "type": "production"},
    ]}})
    node_a = supplier.get("A")

    user = _make_db("user")
    node_b = _make_node(user, "B", "node B")
    node_b.new_edge(input=node_a, type="technosphere", amount=0.5).save()

    user.process()
    assert "supplier" in user.metadata["depends"]


@bw2test
def test_depends_not_duplicated_for_multiple_edges_to_same_db():
    supplier = Database("supplier")
    supplier.write({
        ("supplier", "A"): {"name": "node A", "type": "process", "exchanges": [
            {"input": ("supplier", "A"), "output": ("supplier", "A"), "amount": 1.0, "type": "production"},
        ]},
        ("supplier", "C"): {"name": "node C", "type": "process", "exchanges": [
            {"input": ("supplier", "C"), "output": ("supplier", "C"), "amount": 1.0, "type": "production"},
        ]},
    })
    node_a = supplier.get("A")
    node_c = supplier.get("C")

    user = _make_db("user")
    node_b = _make_node(user, "B", "node B")
    node_b.new_edge(input=node_a, type="technosphere", amount=0.5).save()
    node_b.new_edge(input=node_c, type="technosphere", amount=0.3).save()

    user.process()
    assert user.metadata["depends"].count("supplier") == 1


@bw2test
def test_write_raises_not_implemented():
    db = _make_db("eotw_db")
    with pytest.raises(NotImplementedError):
        db.write({})


@bw2test
def test_efficient_write_many_data_raises_not_implemented():
    db = _make_db("eotw_db")
    with pytest.raises(NotImplementedError):
        db._efficient_write_many_data([])


# ---------------------------------------------------------------------------
# set_config — metadata, dirty flag, filename
# ---------------------------------------------------------------------------


@bw2test
def test_set_config_stores_config_in_metadata():
    db = _make_db("db")
    set_config("db", {"year": 2030})
    assert databases["db"]["eotw_config"] == {"year": 2030}


@bw2test
def test_set_config_none_clears_config_from_metadata():
    db = _make_db("db")
    set_config("db", {"year": 2030})
    set_config("db", None)
    assert "eotw_config" not in databases["db"]


@bw2test
def test_set_config_marks_dirty_when_file_missing():
    db = _make_db("db")
    _make_node(db, "A", "node A")
    set_config("db", {"year": 2030})
    assert databases["db"].get("dirty")


@bw2test
def test_set_config_does_not_mark_dirty_when_file_exists():
    db = _make_db("db")
    _make_node(db, "A", "node A")
    set_config("db", {"year": 2030})
    db.process()
    databases["db"]["dirty"] = False
    databases.flush()
    set_config("db", {"year": 2030})  # same config — file already exists
    assert not databases["db"].get("dirty")


@bw2test
def test_filename_processed_includes_config_hash():
    db = _make_db("db")
    set_config("db", {"year": 2030})
    filename = db.filename_processed()
    assert "db" in filename
    assert filename.endswith(".zip")
    # A different config produces a different filename
    set_config("db", {"year": 2040})
    assert db.filename_processed() != filename


@bw2test
def test_filename_processed_default_when_no_config():
    db = _make_db("db")
    assert db.filename_processed() == db.__class__.__bases__[0].filename_processed(db)


@bw2test
def test_process_uses_metadata_config():
    db = _make_db("db")
    _make_node(db, "A", "node A")
    set_config("db", {"year": 2030})
    db.process()  # no explicit config — should read from metadata
    assert db.filepath_processed().exists()


@bw2test
def test_set_config_context_manager_restores_previous():
    db = _make_db("db")
    _make_node(db, "A", "node A")
    set_config("db", {"year": 2020})
    db.process()

    with set_config("db", {"year": 2030}):
        assert databases["db"]["eotw_config"] == {"year": 2030}

    assert databases["db"]["eotw_config"] == {"year": 2020}


@bw2test
def test_set_config_context_manager_clears_when_no_previous():
    db = _make_db("db")
    _make_node(db, "A", "node A")

    with set_config("db", {"year": 2030}):
        assert "eotw_config" in databases["db"]

    assert "eotw_config" not in databases["db"]


@bw2test
def test_set_config_requires_config_interpreter_raises_without_config():
    from bw_eotw.registry import resolve

    db = _make_db("db")
    node = _make_node(db, "A", "node A")
    node.new_edge(
        input=node,
        type="technosphere",
        amount=1.0,
        interpreter="scenario",
        scenario_values={"baseline": 0.5},
    ).save()

    with pytest.raises(ValueError, match="requires a config"):
        db.process()  # no config set


# ---------------------------------------------------------------------------
# RichEdgesBackend.set_config — method form
# ---------------------------------------------------------------------------


@bw2test
def test_db_set_config_stores_config():
    db = _make_db("db")
    db.set_config({"year": 2030})
    assert databases["db"]["eotw_config"] == {"year": 2030}


@bw2test
def test_db_set_config_none_clears_config():
    db = _make_db("db")
    db.set_config({"year": 2030})
    db.set_config(None)
    assert "eotw_config" not in databases["db"]


@bw2test
def test_db_set_config_context_manager_restores_previous():
    db = _make_db("db")
    _make_node(db, "A", "node A")
    db.set_config({"year": 2020})
    db.process()

    with db.set_config({"year": 2030}):
        assert databases["db"]["eotw_config"] == {"year": 2030}

    assert databases["db"]["eotw_config"] == {"year": 2020}


@bw2test
def test_db_set_config_context_manager_clears_when_no_previous():
    db = _make_db("db")

    with db.set_config({"year": 2030}):
        assert "eotw_config" in databases["db"]

    assert "eotw_config" not in databases["db"]


@bw2test
def test_successive_temporal_context_managers_produce_separate_files():
    """Two back-to-back set_config context managers must each produce their own
    processed file and leave no config in metadata after exit."""
    db = _make_db("db")
    node = _make_node(db, "A", "node A")
    node.new_edge(
        input=node,
        type="technosphere",
        interpreter="temporal",
        temporal_values={2020: 0.5, 2030: 0.8},
        default_year=2020,
    ).save()

    with db.set_config({"year": 2020}):
        assert databases["db"]["eotw_config"] == {"year": 2020}
        db.process()
        file_2020 = db.filepath_processed()
        assert file_2020.exists()

    assert "eotw_config" not in databases["db"]

    with db.set_config({"year": 2030}):
        assert databases["db"]["eotw_config"] == {"year": 2030}
        db.process()
        file_2030 = db.filepath_processed()
        assert file_2030.exists()

    assert "eotw_config" not in databases["db"]
    assert file_2020 != file_2030


# ---------------------------------------------------------------------------
# RichEdge.resolve() — row/col population
# ---------------------------------------------------------------------------


@bw2test
def test_edge_resolve_populates_row_and_col():
    """edge.resolve() must add integer row/col node IDs so interpreters work."""
    db = _make_db("solo")
    node = _make_node(db, "A", "node A")
    bg = Database("bg")
    bg.register()
    coal = bg.new_node(code="coal", name="Coal", type="process")
    coal.save()
    coal.new_edge(input=coal, type="production", amount=1.0).save()

    edge = node.new_edge(
        input=coal,
        type="technosphere",
        interpreter="singlevalue",
        amount=2.5,
    )
    edge.save()

    entries = edge.resolve()
    assert len(entries) == 1
    assert entries[0].amount == 2.5
    assert entries[0].row == coal.id
    assert entries[0].col == node.id


@bw2test
def test_edge_resolve_provider_mix_uses_col_from_output():
    """provider_mix.resolve() must use the output node's integer ID as col."""
    db = _make_db("solo")
    node = _make_node(db, "A", "node A")
    provider = db.new_node(code="P", name="Provider", type="process")
    provider.save()
    provider.new_edge(input=provider, type="production", amount=1.0).save()

    edge = node.new_edge(
        input=provider,
        type="technosphere",
        interpreter="provider_mix",
        product_name="heat",
        amount=1.0,
        mix=[{"input": provider.id, "share": 1.0}],
    )
    edge.save()

    entries = edge.resolve()
    assert len(entries) == 1
    assert entries[0].col == node.id
    assert entries[0].row == provider.id
    assert entries[0].amount == pytest.approx(1.0)
