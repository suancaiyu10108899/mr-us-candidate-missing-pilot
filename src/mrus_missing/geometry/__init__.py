"""C owns predicted-pair geometry. No reference transform argument."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .contracts import (DEGENERATE, ERROR, INSUFFICIENT_MATCHES, INVALID_INPUT, NO_VALID_MODEL,
                        STATUSES, SUCCESS, load_geometry_config, require)
from .io import read_pairs_csv, read_points_csv, source_commit, write_outputs
from .ransac import Estimate, estimate

__all__ = ["fit", "fit_arrays", "Estimate", "estimate", "STATUSES", "SUCCESS",
           "INSUFFICIENT_MATCHES", "DEGENERATE", "NO_VALID_MODEL", "INVALID_INPUT", "ERROR"]


def _load_config(path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite config value: {value}")

    blob = Path(path).read_bytes()
    require(len(blob) <= 1024 * 1024, "config exceeds 1 MiB")
    document = json.loads(blob.decode("utf-8"), parse_constant=reject_constant)
    return load_geometry_config(document)


def _index(identifiers: list[str]) -> dict[str, int]:
    return {identifier: position for position, identifier in enumerate(identifiers)}


def fit_arrays(us_points: np.ndarray, mr_points: np.ndarray,
               geometry: dict[str, Any]) -> Estimate:
    """Fit already-paired coordinates without reading files (used by tests)."""
    return estimate(np.asarray(us_points, dtype=np.float64),
                    np.asarray(mr_points, dtype=np.float64), geometry)


def fit(pairs: Path, mri_points: Path, us_points: Path,
        config: Path, output: Path) -> dict[str, Any]:
    """Fit ``US_TO_MR`` from B's accepted pairs and write the three artefacts.

    Only accepted pairs and coordinates are read; no reference transform or
    correctness label is available to this function.
    """
    settings = _load_config(config)
    rows, pairs_sha256 = read_pairs_csv(Path(pairs))
    mri_ids, mri_xyz = read_points_csv(Path(mri_points))
    us_ids, us_xyz = read_points_csv(Path(us_points))
    mri_index, us_index = _index(mri_ids), _index(us_ids)

    for row in rows:
        require(row["query_id"] in mri_index, f"unknown MRI query: {row['query_id']}")
        require(row["candidate_id"] in us_index, f"unknown US candidate: {row['candidate_id']}")
    us_rows = np.asarray([us_xyz[us_index[row["candidate_id"]]] for row in rows], dtype=np.float64)
    mr_rows = np.asarray([mri_xyz[mri_index[row["query_id"]]] for row in rows], dtype=np.float64)

    result = estimate(us_rows, mr_rows, settings)
    commit = source_commit()
    write_outputs(Path(output), result, rows, settings, pairs_sha256, commit)
    return {
        "status": result.status,
        "status_detail": result.detail,
        "direction": settings["direction"],
        "unit": settings["unit"],
        "pair_count": len(rows),
        "inlier_count": result.inlier_count,
        "pairs_sha256": pairs_sha256,
        "source_commit": commit,
        "output": str(Path(output)),
    }
