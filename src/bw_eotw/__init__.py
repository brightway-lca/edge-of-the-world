"""bw_eotw — edge-of-the-world: an alternate Brightway backend with rich edges."""

__all__ = (
    "__version__",
    "MatrixEntry",
    "RichEdge",
    "RichEdges",
    "RichEdgesBackend",
    "RichNode",
    "register",
    "register_validator",
    "resolve",
    "validate_edge",
)

__version__ = "0.0.1"

from bw2data.subclass_mapping import DATABASE_BACKEND_MAPPING, NODE_PROCESS_CLASS_MAPPING

from bw_eotw.backend import RichEdgesBackend
from bw_eotw.edge_classes import RichEdge, RichEdges
from bw_eotw.matrix_entry import MatrixEntry
from bw_eotw.node_classes import RichNode
from bw_eotw.registry import register, register_validator, resolve, validate_edge

import bw_eotw.interpreters  # noqa: F401 — triggers interpreter registration

DATABASE_BACKEND_MAPPING["eotw"] = RichEdgesBackend
NODE_PROCESS_CLASS_MAPPING["eotw"] = RichNode
