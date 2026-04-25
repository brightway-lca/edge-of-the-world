import pytest
from bw2data.database import Database
from bw2data.tests import bw2test

import bw_eotw  # noqa: F401 — registers the backend


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
def test_config_passed_to_interpreter_during_process():
    db = _make_db("solo")
    _make_node(db, "X", "node X")
    db.process(config={"year": 2030})
    db.process(config=None)
    db.process()


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
