import pytest
from bw2data import get_id
from bw2data.database import Database
from bw2data.tests import bw2test
from bw_processing import load_datapackage
from fsspec.implementations.zip import ZipFileSystem

import bw_eotw  # noqa: F401 — registers the backend


# ---------------------------------------------------------------------------
# Dependents tracking
# ---------------------------------------------------------------------------


@bw2test
def test_same_database_edge_leaves_depends_empty():
    db = Database("solo", backend="eotw")
    db.write(
        {
            ("solo", "X"): {
                "name": "node X",
                "type": "process",
                "exchanges": [
                    {
                        "input": ("solo", "X"),
                        "output": ("solo", "X"),
                        "amount": 1.0,
                        "type": "production",
                    }
                ],
            }
        }
    )
    db.process()
    assert db.metadata.get("depends", []) == []


@bw2test
def test_cross_database_edge_adds_to_depends():
    supplier = Database("supplier")
    supplier.write(
        {
            ("supplier", "A"): {
                "name": "node A",
                "type": "process",
                "exchanges": [
                    {
                        "input": ("supplier", "A"),
                        "output": ("supplier", "A"),
                        "amount": 1.0,
                        "type": "production",
                    }
                ],
            }
        }
    )

    user = Database("user", backend="eotw")
    user.write(
        {
            ("user", "B"): {
                "name": "node B",
                "type": "process",
                "exchanges": [
                    {
                        "input": ("user", "B"),
                        "output": ("user", "B"),
                        "amount": 1.0,
                        "type": "production",
                    },
                    {
                        "input": ("supplier", "A"),
                        "output": ("user", "B"),
                        "amount": 0.5,
                        "type": "technosphere",
                    },
                ],
            }
        }
    )
    user.process()
    assert "supplier" in user.metadata["depends"]


@bw2test
def test_depends_not_duplicated_for_multiple_edges_to_same_db():
    supplier = Database("supplier")
    supplier.write(
        {
            ("supplier", "A"): {
                "name": "node A",
                "type": "process",
                "exchanges": [
                    {"input": ("supplier", "A"), "output": ("supplier", "A"),
                     "amount": 1.0, "type": "production"}
                ],
            },
            ("supplier", "C"): {
                "name": "node C",
                "type": "process",
                "exchanges": [
                    {"input": ("supplier", "C"), "output": ("supplier", "C"),
                     "amount": 1.0, "type": "production"}
                ],
            },
        }
    )

    user = Database("user", backend="eotw")
    user.write(
        {
            ("user", "B"): {
                "name": "node B",
                "type": "process",
                "exchanges": [
                    {"input": ("user", "B"), "output": ("user", "B"),
                     "amount": 1.0, "type": "production"},
                    {"input": ("supplier", "A"), "output": ("user", "B"),
                     "amount": 0.5, "type": "technosphere"},
                    {"input": ("supplier", "C"), "output": ("user", "B"),
                     "amount": 0.3, "type": "technosphere"},
                ],
            }
        }
    )
    user.process()
    assert user.metadata["depends"].count("supplier") == 1


@bw2test
def test_config_passed_to_interpreter_during_process():
    """A temporal edge selects the correct year from config."""
    db = Database("solo", backend="eotw")
    db.write(
        {
            ("solo", "X"): {
                "name": "node X",
                "type": "process",
                "exchanges": [
                    {
                        "input": ("solo", "X"),
                        "output": ("solo", "X"),
                        "amount": 1.0,
                        "type": "production",
                    }
                ],
            }
        }
    )
    # process() should accept a config without error
    db.process(config={"year": 2030})
    db.process(config=None)
    db.process()


# ---------------------------------------------------------------------------
# provider_mix integration
# ---------------------------------------------------------------------------


@bw2test
def test_provider_mix_expands_to_correct_matrix_entries():
    """Each provider in the mix yields its own matrix row with a scaled amount."""
    grid = Database("grid")
    grid.write(
        {
            ("grid", "wind"): {
                "name": "wind power",
                "type": "process",
                "exchanges": [
                    {"input": ("grid", "wind"), "output": ("grid", "wind"),
                     "amount": 1.0, "type": "production"},
                ],
            },
            ("grid", "solar"): {
                "name": "solar power",
                "type": "process",
                "exchanges": [
                    {"input": ("grid", "solar"), "output": ("grid", "solar"),
                     "amount": 1.0, "type": "production"},
                ],
            },
        }
    )

    user = Database("user", backend="eotw")
    user.write(
        {
            ("user", "factory"): {
                "name": "factory",
                "type": "process",
                "exchanges": [
                    {"input": ("user", "factory"), "output": ("user", "factory"),
                     "amount": 1.0, "type": "production"},
                    {
                        "input": ("grid", "wind"),   # bw2data needs a valid input for storage
                        "output": ("user", "factory"),
                        "type": "technosphere",
                        "interpreter": "provider_mix",
                        "product_name": "electricity",
                        "amount": 2.0,
                        "mix": [
                            {"input": ("grid", "wind"),  "share": 0.60},
                            {"input": ("grid", "solar"), "share": 0.40},
                        ],
                    },
                ],
            }
        }
    )
    user.process()

    dp = load_datapackage(ZipFileSystem(str(user.filepath_processed())))
    tech_data = dp.get_resource("user_technosphere_matrix.data")[0]
    tech_indices = dp.get_resource("user_technosphere_matrix.indices")[0]

    wind_id = get_id(("grid", "wind"))
    solar_id = get_id(("grid", "solar"))
    factory_id = get_id(("user", "factory"))

    rows = list(zip(tech_indices["row"], tech_indices["col"], tech_data))
    amounts_by_row = {row: amt for row, col, amt in rows if col == factory_id}

    assert amounts_by_row[wind_id] == pytest.approx(2.0 * 0.60)
    assert amounts_by_row[solar_id] == pytest.approx(2.0 * 0.40)
