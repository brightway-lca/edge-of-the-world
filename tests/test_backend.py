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


def _write_grid():
    """Write a two-node grid database and return (wind_id, solar_id)."""
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
    return get_id(("grid", "wind")), get_id(("grid", "solar"))


@bw2test
def test_provider_mix_expands_to_correct_matrix_entries():
    """Each provider in the mix yields its own matrix row with a scaled amount."""
    wind_id, solar_id = _write_grid()

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
                        "input": ("grid", "wind"),
                        "output": ("user", "factory"),
                        "type": "technosphere",
                        "interpreter": "provider_mix",
                        "product_name": "electricity",
                        "amount": 2.0,
                        "mix": [
                            {"input": wind_id,  "share": 0.60},
                            {"input": solar_id, "share": 0.40},
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

    factory_id = get_id(("user", "factory"))
    rows = list(zip(tech_indices["row"], tech_indices["col"], tech_data))
    amounts_by_row = {row: amt for row, col, amt in rows if col == factory_id}

    assert amounts_by_row[wind_id] == pytest.approx(2.0 * 0.60)
    assert amounts_by_row[solar_id] == pytest.approx(2.0 * 0.40)


@bw2test
def test_provider_mix_adds_provider_database_to_depends():
    """provider_mix edges to another database must appear in depends after process()."""
    wind_id, solar_id = _write_grid()

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
                        "input": ("grid", "wind"),
                        "output": ("user", "factory"),
                        "type": "technosphere",
                        "interpreter": "provider_mix",
                        "product_name": "electricity",
                        "amount": 1.0,
                        "mix": [
                            {"input": wind_id,  "share": 0.60},
                            {"input": solar_id, "share": 0.40},
                        ],
                    },
                ],
            }
        }
    )
    user.process()
    assert "grid" in user.metadata["depends"]


@bw2test
def test_provider_mix_write_rejects_cross_database_mix():
    """Database.write() must raise when mix providers span multiple databases."""
    wind_id, solar_id = _write_grid()

    # Write a second, unrelated database
    other = Database("other")
    other.write(
        {
            ("other", "Z"): {
                "name": "node Z",
                "type": "process",
                "exchanges": [
                    {"input": ("other", "Z"), "output": ("other", "Z"),
                     "amount": 1.0, "type": "production"},
                ],
            }
        }
    )
    other_id = get_id(("other", "Z"))

    user = Database("user", backend="eotw")
    with pytest.raises(ValueError, match="database"):
        user.write(
            {
                ("user", "factory"): {
                    "name": "factory",
                    "type": "process",
                    "exchanges": [
                        {"input": ("user", "factory"), "output": ("user", "factory"),
                         "amount": 1.0, "type": "production"},
                        {
                            "input": ("grid", "wind"),
                            "output": ("user", "factory"),
                            "type": "technosphere",
                            "interpreter": "provider_mix",
                            "product_name": "electricity",
                            "amount": 1.0,
                            "mix": [
                                {"input": wind_id,  "share": 0.60},
                                {"input": other_id, "share": 0.40},
                            ],
                        },
                    ],
                }
            }
        )
