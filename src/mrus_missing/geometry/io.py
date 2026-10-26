"""File contracts for C: pairs CSV in, three fit artefacts out.

The readers accept only the columns they need and reject conflicting or
non-finite values. Writers never overwrite an existing run directory, so a
retry always needs a new ``--output`` path (protocol section 8).
"""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from .contracts import require
from .ransac import Estimate

PAIR_COLUMNS = ("condition_id", "method_id", "query_id", "candidate_id", "d1", "d2", "ratio")
POINT_COLUMNS = ("point_id", "i", "j", "k")
INLIER_COLUMNS = ("query_id", "candidate_id", "inlier", "residual")


def read_points_csv(path: Path) -> tuple[list[str], np.ndarray]:
    """Read ``point_id,i,j,k`` coordinates in index units, preserving file order."""
    require(path.is_file(), f"missing points file: {path}")
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    require(rows, "points CSV is empty")
    require(all(set(POINT_COLUMNS) <= set(row) for row in rows), "points CSV needs point_id,i,j,k")
    identifiers: list[str] = []
    coordinates: list[list[float]] = []
    for row in rows:
        identifier = row["point_id"]
        require(bool(identifier), "empty point_id")
        try:
            values = [float(row[key]) for key in ("i", "j", "k")]
        except (TypeError, ValueError) as error:
            raise ValueError(f"non-numeric coordinate for {identifier}") from error
        require(all(np.isfinite(values)), f"non-finite coordinate for {identifier}")
        identifiers.append(identifier)
        coordinates.append(values)
    require(len(set(identifiers)) == len(identifiers), "duplicate point_id")
    return identifiers, np.asarray(coordinates, dtype=np.float64)


def read_pairs_csv(path: Path) -> tuple[list[dict[str, str]], str]:
    """Read B's accepted pairs and return the file digest used for identity."""
    require(path.is_file(), f"missing pairs file: {path}")
    blob = path.read_bytes()
    rows = list(csv.DictReader(blob.decode("utf-8").splitlines()))
    require(rows, "pairs CSV is empty")
    require(all("query_id" in row and "candidate_id" in row for row in rows),
            "pairs CSV needs query_id and candidate_id")
    for row in rows:
        require(bool(row["query_id"]) and bool(row["candidate_id"]), "empty pair identifier")
    queries = [row["query_id"] for row in rows]
    require(len(set(queries)) == len(queries), "duplicate query_id in pairs")
    return rows, hashlib.sha256(blob).hexdigest()


def source_commit(start: Path | None = None) -> str | None:
    """Report the actual checkout commit; ``None`` when git cannot answer."""
    root = start or Path(__file__).resolve().parents[3]
    try:
        result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit if result.returncode == 0 and len(commit) == 40 else None


def _number(value: float) -> str:
    return f"{float(value):.17g}"


def write_outputs(output: Path, estimate: Estimate, pairs: Iterable[dict[str, str]],
                  config: dict[str, Any], pairs_sha256: str, commit: str | None) -> dict[str, Any]:
    """Create a fresh output directory with transform, inliers and diagnostics."""
    output = Path(output)
    require(not output.exists(), f"output already exists: {output}")
    output.mkdir(parents=True, exist_ok=False)

    rows = list(pairs)
    healthy = estimate.status == "SUCCESS"
    transform = {
        "direction": config["direction"],
        "unit": config["unit"],
        "status": estimate.status,
        "R": None if not healthy else [[float(x) for x in row] for row in estimate.rotation],
        "t": None if not healthy else [float(x) for x in estimate.translation],
        "fit_config": {key: config[key] for key in sorted(config)},
        "pairs_sha256": pairs_sha256,
        "source_commit": commit,
    }
    with (output / "transform.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(transform, ensure_ascii=False, sort_keys=True, indent=2,
                                allow_nan=False) + "\n")

    inliers: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        accepted = bool(estimate.inliers[index]) if index < estimate.inliers.size else False
        value = estimate.residuals[index] if index < estimate.residuals.size else float("nan")
        inliers.append({
            "query_id": row["query_id"],
            "candidate_id": row["candidate_id"],
            "inlier": "true" if accepted else "false",
            "residual": "" if not np.isfinite(value) else _number(value),
        })
    with (output / "inliers.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=INLIER_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(inliers)

    diagnostics = dict(estimate.diagnostics)
    diagnostics["pairs_sha256"] = pairs_sha256
    diagnostics["status"] = estimate.status
    diagnostics["status_detail"] = estimate.detail
    diagnostics["source_commit"] = commit
    finite = estimate.residuals[np.isfinite(estimate.residuals)] if estimate.residuals.size else np.zeros(0)
    selected = estimate.residuals[estimate.inliers] if estimate.inliers.size else np.zeros(0)
    diagnostics["residual_summary"] = {
        "all_max": float(finite.max()) if finite.size else None,
        "inlier_mean": float(selected.mean()) if selected.size else None,
        "inlier_max": float(selected.max()) if selected.size else None,
    }
    with (output / "fit_diagnostics.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(diagnostics, ensure_ascii=False, sort_keys=True, indent=2,
                                allow_nan=False) + "\n")
    return transform
