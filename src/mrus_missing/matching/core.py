"""Descriptor-only matching under PROTOCOL v1; no file or geometry access."""

from collections.abc import Mapping, Sequence
import hashlib
import json
import math
from typing import Any

import numpy as np


QUERY_FIELDS = (
    "condition_id", "method_id", "query_id", "query_row", "nearest_id",
    "second_id", "d1", "d2", "ratio", "forward_unique", "reverse_unique",
    "mutual", "ratio_pass", "accepted", "accepted_candidate_id", "rejection_reason",
)
PAIR_FIELDS = (
    "condition_id", "method_id", "query_id", "candidate_id", "d1", "d2", "ratio",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError("INVALID_INPUT: " + message)


def _settings(config: Mapping) -> dict:
    """Read numerical rules from the caller's experiment configuration."""
    _require(isinstance(config, Mapping) and config.get("protocol_version") == "1.0",
             "expected protocol_version 1.0")
    spec = config.get("matching")
    _require(isinstance(spec, Mapping), "matching configuration required")
    required = {
        "source_dtype": "float32", "dtype": "float64", "distance": "L2",
        "renormalize": False, "tie_rule": "distance_minus_min_le_eps",
        "ratio_comparison": "strict_lt", "reverse_ratio": False,
        "reverse_query_set": "all_64",
    }
    for key, expected in required.items():
        value = spec.get(key)
        _require(type(value) is type(expected) and value == expected,
                 f"unsupported matching configuration: {key}")
    for key in ("eps", "ratio_threshold"):
        value = spec.get(key)
        _require(type(value) in (int, float) and math.isfinite(value) and value > 0,
                 f"positive finite {key} required")
    _require(spec["ratio_threshold"] < 1, "ratio threshold must be below one")
    # No numerical defaults: the handoff's experiment config supplies both values.
    return dict(spec)


def _descriptors(values: np.ndarray, name: str, eps: float) -> np.ndarray:
    _require(isinstance(values, np.ndarray) and values.ndim == 2,
             f"{name} must be a two-dimensional NumPy array")
    _require(values.dtype == np.float32 and values.shape[1] > 0,
             f"{name} requires float32 and a positive dimension")
    _require(bool(np.isfinite(values).all()), f"{name} contains nonfinite values")
    converted = values.astype(np.float64, copy=True)
    _require(bool((np.linalg.norm(converted, axis=1) > eps).all()),
             f"{name} contains zero or near-zero descriptors")
    return converted


def l2_distances(mri_descriptors: np.ndarray, us_descriptors: np.ndarray,
                 *, config: Mapping) -> np.ndarray:
    """Return float64[Nq,Nc] ordinary L2; preserve input arrays byte for byte.

    Small N/D are supported for artificial tests. Empty candidates have shape
    (0,D); the query set must be nonempty and is never internally filtered.
    """
    spec = _settings(config)
    queries = _descriptors(mri_descriptors, "MRI", spec["eps"])
    candidates = _descriptors(us_descriptors, "US", spec["eps"])
    _require(len(queries) > 0, "MRI query set must be nonempty")
    _require(queries.shape[1] == candidates.shape[1], "descriptor dimensions differ")
    delta = queries[:, None, :] - candidates[None, :, :]
    distances = np.sqrt(np.sum(delta * delta, axis=2, dtype=np.float64))
    _require(bool(np.isfinite(distances).all()), "nonfinite L2 distances")
    return distances


def _ids(values: Sequence, count: int, name: str) -> list[str]:
    _require(isinstance(values, (list, tuple)) and len(values) == count,
             f"{name} count mismatch")
    _require(all(isinstance(x, str) and bool(x.strip()) for x in values),
             f"{name} must be nonempty strings")
    _require(len(set(values)) == count, f"duplicate {name}")
    return list(values)


def _sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode("utf-8")).hexdigest()


def _descriptor_sha256(values: np.ndarray) -> str:
    """Hash the selected array's dtype/shape/bytes, not a source NPY file."""
    header = json.dumps([str(values.dtype), list(values.shape)], separators=(",", ":"))
    return hashlib.sha256(header.encode("ascii") + b"\n" + values.tobytes(order="C")).hexdigest()


def _query_record(distances: np.ndarray, row: int, query_id: str,
                  candidate_ids: list[str], reverse_indices: np.ndarray,
                  reverse_unique: np.ndarray, condition_id: str, method_id: str,
                  eps: float, threshold: float) -> dict:
    count = len(candidate_ids)
    d = distances[row]
    q = dict(zip(QUERY_FIELDS, (condition_id, method_id, query_id, row,
                 None, None, None, None, None, False, False, False, False,
                 False, None, None)))
    if count:
        ordered = np.sort(d)
        q["d1"] = float(ordered[0])
        q["d2"] = float(ordered[1]) if count >= 2 else None
        near = np.flatnonzero(d - ordered[0] <= eps)
        q["forward_unique"] = len(near) == 1
        if q["forward_unique"]:
            nearest = int(near[0])
            q["nearest_id"] = candidate_ids[nearest]
            q["reverse_unique"] = bool(reverse_unique[nearest])
            q["mutual"] = bool(reverse_unique[nearest] and reverse_indices[nearest] == row)
            if count >= 2:
                # An ambiguous second identity is null; d2 is still well-defined.
                second = np.flatnonzero((np.arange(count) != nearest)
                                        & (np.abs(d - ordered[1]) <= eps))
                if len(second) == 1:
                    q["second_id"] = candidate_ids[int(second[0])]
        # Tied nearest identities are null, never resolved by row/ID ordering.
        if q["d2"] is not None and q["d2"] > eps:
            q["ratio"] = q["d1"] / q["d2"]
            q["ratio_pass"] = q["ratio"] < threshold
    if count < (2 if method_id == "MNN_RATIO" else 1):
        reason = "insufficient_candidates"
    elif not q["forward_unique"]:
        reason = "forward_ambiguity"
    elif method_id == "MNN_RATIO" and not q["ratio_pass"]:
        reason = "ratio"
    elif not q["reverse_unique"]:
        reason = "reverse_ambiguity"
    elif not q["mutual"]:
        reason = "not_mutual"
    else:
        reason = None
    q["rejection_reason"] = reason
    q["accepted"] = reason is None
    q["accepted_candidate_id"] = q["nearest_id"] if q["accepted"] else None
    return q


def match_descriptors(mri_descriptors: np.ndarray, us_descriptors: np.ndarray,
                      query_ids: Sequence[str], candidate_ids: Sequence[str],
                      candidate_source_rows: Sequence[int], *, condition_id: str,
                      method_id: str, release_id: str, config: Mapping) -> dict:
    """Produce queries/pairs/diagnostics from current candidates only.

    This pure API supports small artificial sets and all supplied MRI queries.
    Use match_inputs for the strict release-v1 loader contract. Invalid input
    raises ValueError(INVALID_INPUT) for the whole call; no rows are dropped.
    """
    spec = _settings(config)
    _require(method_id in ("MNN", "MNN_RATIO"), "unknown method_id")
    for name, value in (("condition_id", condition_id), ("release_id", release_id)):
        _require(isinstance(value, str) and bool(value.strip()), f"{name} required")
    distances = l2_distances(mri_descriptors, us_descriptors, config=config)
    n, k = distances.shape
    qids = _ids(query_ids, n, "query_ids")
    cids = _ids(candidate_ids, k, "candidate_ids")
    _require(isinstance(candidate_source_rows, (list, tuple))
             and len(candidate_source_rows) == k, "candidate_source_rows count mismatch")
    rows = list(candidate_source_rows)
    _require(all(type(x) is int and x >= 0 for x in rows), "invalid candidate source row")
    _require(rows == sorted(set(rows)), "candidate source rows must be unique/in source order")
    if k:
        reverse_indices = np.argmin(distances, axis=0)
        reverse_min = distances[reverse_indices, np.arange(k)]
        reverse_unique = np.sum(distances - reverse_min[None, :] <= spec["eps"], axis=0) == 1
    else:
        reverse_indices = np.empty(0, dtype=np.int64)
        reverse_unique = np.empty(0, dtype=bool)
    queries = [_query_record(distances, i, qid, cids, reverse_indices,
                            reverse_unique, condition_id, method_id,
                            spec["eps"], spec["ratio_threshold"])
               for i, qid in enumerate(qids)]
    pairs = [{key: q["accepted_candidate_id"] if key == "candidate_id" else q[key]
              for key in PAIR_FIELDS} for q in queries if q["accepted"]]
    diagnostics = {
        "status": "SUCCESS", "protocol_version": config["protocol_version"],
        "release_id": release_id, "condition_id": condition_id, "method_id": method_id,
        "query_count": n, "candidate_count": k, "dimension": mri_descriptors.shape[1],
        "source_dtype": str(mri_descriptors.dtype), "compute_dtype": str(distances.dtype),
        "reverse_query_count": n, "matching_config": spec,
        "candidate_binding": [{"candidate_id": cid, "source_row": source_row}
                              for cid, source_row in zip(cids, rows)],
        "ambiguous_identity": "null; distances retained; no ID/row tie breaking",
        "ratio_pass_definition": "d2 > eps and d1/d2 < ratio_threshold",
        "input_sha256": {
            "mri_descriptor_content": _descriptor_sha256(mri_descriptors),
            "us_selected_descriptor_content": _descriptor_sha256(us_descriptors),
            "identity": _sha256([release_id, condition_id, qids, cids, rows]),
            "matching_config": _sha256([config["protocol_version"], spec]),
        },
    }
    return {"queries": queries, "pairs": pairs, "diagnostics": diagnostics}


def match_inputs(inputs: Mapping, *, condition_id: str, method_id: str,
                 config: Mapping) -> dict:
    """Consume exactly load_matching_inputs' descriptor-only release-v1 dict.

    The public loader authenticates source payloads, candidate membership and
    source row bindings. This adapter enforces the configured full query set;
    neither the loader nor this function uses geometry to predict matches.
    """
    names = {"mri_descriptors", "us_descriptors", "query_ids", "candidate_ids",
             "candidate_source_rows", "release_id"}
    _require(isinstance(inputs, Mapping) and set(inputs) == names,
             "expected descriptor-only preparation API fields")
    spec = _settings(config)
    n, d = spec.get("query_count"), spec.get("dimension")
    _require(type(n) is int and n > 0 and type(d) is int and d > 0,
             "configured query_count/dimension required")
    mri, us = inputs["mri_descriptors"], inputs["us_descriptors"]
    _require(isinstance(mri, np.ndarray) and mri.shape == (n, d),
             "complete configured MRI query set required")
    _require(isinstance(us, np.ndarray) and us.ndim == 2 and us.shape[1] == d,
             "configured US descriptor dimension required")
    rows = inputs["candidate_source_rows"]
    # In release-v1 both original modality arrays have query_count rows.
    _require(isinstance(rows, (list, tuple))
             and all(type(i) is int and 0 <= i < n for i in rows),
             "release-v1 candidate source rows out of bounds")
    return match_descriptors(mri, us, inputs["query_ids"], inputs["candidate_ids"],
                             rows, condition_id=condition_id, method_id=method_id,
                             release_id=inputs["release_id"], config=config)
