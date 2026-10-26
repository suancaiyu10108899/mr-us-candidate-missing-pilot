"""Fixed geometry contract for protocol v1 (US_TO_MR, index units).

The values here mirror ``configs/experiment-v1.json`` and PROTOCOL section 6.
C refuses a configuration that differs instead of silently running a
different protocol; the thresholds are scientific parameters, not tuning
knobs.
"""
from __future__ import annotations

from typing import Any

SUCCESS = "SUCCESS"
INSUFFICIENT_MATCHES = "INSUFFICIENT_MATCHES"
DEGENERATE = "DEGENERATE"
NO_VALID_MODEL = "NO_VALID_MODEL"
INVALID_INPUT = "INVALID_INPUT"
ERROR = "ERROR"

STATUSES = (SUCCESS, INSUFFICIENT_MATCHES, DEGENERATE, NO_VALID_MODEL, INVALID_INPUT, ERROR)

GEOMETRY_V1: dict[str, Any] = {
    "direction": "US_TO_MR",
    "unit": "index_unit",
    "rng": "PCG64",
    "seed": 20261005,
    "max_iterations": 256,
    "sample_size": 3,
    "minimum_rank": 2,
    "rank_tolerance": "smax*max(n,3)*float64_eps",
    "inlier_threshold": 1.0,
    "inlier_comparison": "le",
    "minimum_final_inliers": 4,
    "reflection_allowed": False,
    "refit": "once_then_recompute_inliers_and_rank",
    "tie_break": "inlier_count_then_inlier_squared_error_then_first_sample",
}


def require(condition: bool, message: str) -> None:
    """Raise the same input error type the rest of the repository uses."""
    if not condition:
        raise ValueError(message)


def load_geometry_config(document: dict[str, Any]) -> dict[str, Any]:
    """Extract and validate the fixed geometry block of an experiment config.

    The whole ``geometry`` object must equal :data:`GEOMETRY_V1`; a partial or
    edited block is an input error, never a reason to fall back to defaults.
    """
    require(isinstance(document, dict), "experiment config must be an object")
    block = document.get("geometry")
    require(isinstance(block, dict), "experiment config needs a geometry object")
    require(set(block) == set(GEOMETRY_V1), "geometry keys differ from protocol v1")
    for key, expected in GEOMETRY_V1.items():
        actual = block[key]
        require(type(actual) is type(expected) and actual == expected,
                f"geometry.{key} differs from protocol v1")
    return dict(GEOMETRY_V1)
