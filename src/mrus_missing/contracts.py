"""Small synthetic interface reader, not a scientific release validator."""

import json
import math
from pathlib import Path
from typing import Any


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _finite(value: Any) -> bool:
    return type(value) in (float, int) and math.isfinite(value)


def validate_fixture(data: dict[str, Any]) -> dict[str, Any]:
    """Validate artificial descriptor/point binding and candidate partition.

    Parameters
    ----------
    data : dict
        An explicitly labelled interface fixture, with no research provenance.

    Returns
    -------
    dict
        Structural summary. No matching, fitting or evaluation is performed.
    """
    _require(isinstance(data, dict), "fixture must be an object")
    _require(data.get("kind") == "synthetic_fixture", "synthetic_fixture required")
    _require(data.get("schema_version") == "interface-v1", "unknown fixture schema")
    _require(data.get("scientific_result") is False, "fixture is not a scientific result")
    ordered_ids: dict[str, list[str]] = {}
    dimensions = []
    for modality in ("mri", "us"):
        block = data.get(modality)
        _require(isinstance(block, dict), f"missing {modality} object")
        vectors = block.get("descriptors")
        points = block.get("points")
        _require(isinstance(vectors, list) and len(vectors) > 0, "vectors required")
        _require(isinstance(points, list) and len(points) == len(vectors), "point count mismatch")
        _require(isinstance(vectors[0], list) and len(vectors[0]) > 0, "empty vector")
        width = len(vectors[0])
        dimensions.append(width)
        for vector in vectors:
            _require(isinstance(vector, list) and len(vector) == width, "ragged vectors")
            _require(all(_finite(x) for x in vector), "nonfinite descriptor")
            _require(math.hypot(*vector) > 1e-12, "zero descriptor")
        ids, rows = [], []
        for point in points:
            _require(isinstance(point, dict), "point must be an object")
            point_id, row = point.get("point_id"), point.get("descriptor_row")
            _require(isinstance(point_id, str) and bool(point_id), "point_id required")
            _require(type(row) is int, "descriptor_row must be an integer")
            _require(all(_finite(point.get(k)) for k in ("i", "j", "k")), "nonfinite coordinate")
            _require(isinstance(point.get("source_id"), str) and bool(point["source_id"]), "source_id required")
            ids.append(point_id)
            rows.append(row)
        _require(len(set(ids)) == len(ids), "duplicate point_id")
        _require(sorted(rows) == list(range(len(vectors))), "descriptor_row coverage")
        ordered_ids[modality] = [p["point_id"] for p in sorted(points, key=lambda p: p["descriptor_row"])]
    _require(dimensions[0] == dimensions[1], "descriptor dimensions differ")
    candidates = data.get("candidates")
    _require(isinstance(candidates, dict), "candidates required")
    keep, remove = candidates.get("keep_ids"), candidates.get("remove_ids")
    for values in (keep, remove):
        _require(isinstance(values, list) and all(isinstance(x, str) for x in values), "candidate IDs required")
        _require(len(set(values)) == len(values), "duplicate candidate ID")
    _require(not set(keep) & set(remove), "candidate sets overlap")
    _require(set(keep) | set(remove) == set(ordered_ids["us"]), "candidate partition mismatch")
    return {
        "kind": "synthetic_fixture", "status": "STRUCTURE_VALID",
        "scientific_result": False, "algorithm_executed": False,
        "mri_count": len(ordered_ids["mri"]), "us_count": len(ordered_ids["us"]),
        "dimension": dimensions[0], "ordered_point_ids": ordered_ids,
        "kept_ids_in_source_order": [x for x in ordered_ids["us"] if x in keep],
    }


def inspect_fixture(path: Path) -> dict[str, Any]:
    """Read a small artificial JSON file and validate only its interface."""
    if path.stat().st_size > 64 * 1024:
        raise ValueError("fixture exceeds 64 KiB")
    with path.open(encoding="utf-8") as stream:
        return validate_fixture(json.load(stream))
