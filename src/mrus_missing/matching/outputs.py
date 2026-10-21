"""Write protocol matching files to a new directory; no research-data reader."""

from collections.abc import Mapping
import csv
from datetime import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re

from .core import PAIR_FIELDS, QUERY_FIELDS, _require


def _encode_json(value: Mapping) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def _csv_bytes(rows: list[dict], fields: tuple[str, ...]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def _check_result(result: Mapping) -> None:
    _require(isinstance(result, Mapping) and set(result) == {"queries", "pairs", "diagnostics"},
             "matching result fields differ")
    queries, pairs, diagnostics = (result[k] for k in ("queries", "pairs", "diagnostics"))
    _require(isinstance(queries, list) and isinstance(pairs, list)
             and isinstance(diagnostics, dict), "invalid matching result types")
    _require(bool(queries) and all(set(q) == set(QUERY_FIELDS) for q in queries),
             "query schema differs")
    _require(all(set(p) == set(PAIR_FIELDS) for p in pairs), "pair schema differs")
    _require([q["query_row"] for q in queries] == list(range(len(queries)))
             and len({q["query_id"] for q in queries}) == len(queries), "query identity/order differs")
    _require(diagnostics["status"] == "SUCCESS"
             and diagnostics["query_count"] == len(queries), "matching status/count differs")
    for q in queries:
        _require(all(type(q[k]) is bool for k in ("forward_unique", "reverse_unique", "mutual",
                                                  "ratio_pass", "accepted")), "invalid flags")
        _require(all(q[k] == diagnostics[k] for k in ("condition_id", "method_id")),
                 "mixed matching identities")
        _require(q["accepted"] == (q["rejection_reason"] is None), "acceptance/reason mismatch")
        _require(q["rejection_reason"] in (None, "insufficient_candidates", "forward_ambiguity",
                                           "ratio", "reverse_ambiguity", "not_mutual"),
                 "unknown rejection reason")
        _require(all(q[k] is None or (type(q[k]) in (int, float)
                     and math.isfinite(q[k]) and q[k] >= 0) for k in ("d1", "d2", "ratio")),
                 "query contains invalid distances/ratio")
        if q["accepted"]:
            _require(q["forward_unique"] and q["reverse_unique"] and q["mutual"]
                     and q["accepted_candidate_id"] == q["nearest_id"]
                     and q["nearest_id"] is not None, "invalid accepted query")
            _require(q["method_id"] != "MNN_RATIO" or q["ratio_pass"], "accepted ratio failed")
        else:
            _require(q["accepted_candidate_id"] is None, "rejected query contains accepted ID")
    expected = [{k: q["accepted_candidate_id"] if k == "candidate_id" else q[k]
                 for k in PAIR_FIELDS} for q in queries if q["accepted"]]
    _require(pairs == expected, "pairs are not the exact accepted-query mapping")
    _require(len({p["candidate_id"] for p in pairs}) == len(pairs), "candidate accepted twice")
    allowed = {x["candidate_id"] for x in diagnostics["candidate_binding"]}
    _require(len(allowed) == diagnostics["candidate_count"], "candidate identity/count differs")
    _require(all(q[k] is None or q[k] in allowed for q in queries
                 for k in ("nearest_id", "second_id", "accepted_candidate_id")),
             "query references a missing candidate")
    _require(isinstance(diagnostics["input_sha256"], dict)
             and bool(diagnostics["input_sha256"])
             and all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                     for value in diagnostics["input_sha256"].values()), "invalid input hashes")


def write_match_outputs(result: Mapping, output: Path, *, run_metadata: Mapping) -> dict:
    """Write queries.csv, pairs.csv, match_diagnostics.json and binding RUN.json.

    Numerical output is deterministic; run identities/times are explicit caller
    metadata. Preflight validation precedes directory creation. Never overwrite
    an existing output directory, even if empty. This writer runs no algorithm.
    """
    _check_result(result)
    required = {"run_id", "source_commit", "source_dirty", "mode", "operator", "command",
                "dependencies", "started_at", "ended_at"}
    _require(isinstance(run_metadata, Mapping) and set(run_metadata) == required,
             "RUN metadata fields differ")
    for key in ("run_id", "operator", "command"):
        _require(isinstance(run_metadata[key], str) and bool(run_metadata[key].strip()),
                 f"RUN {key} required")
    _require(isinstance(run_metadata["source_commit"], str)
             and re.fullmatch(r"[0-9a-f]{40}", run_metadata["source_commit"]) is not None,
             "RUN requires a full source commit")
    _require(type(run_metadata["source_dirty"]) is bool, "RUN source_dirty must be boolean")
    _require(run_metadata["mode"] in ("debug", "formal"), "unknown run mode")
    _require(not run_metadata["source_dirty"] or run_metadata["mode"] == "debug",
             "dirty source can only produce debug output")
    _require(isinstance(run_metadata["dependencies"], Mapping)
             and bool(run_metadata["dependencies"]), "dependency versions required")
    times = []
    for key in ("started_at", "ended_at"):
        try:
            value = datetime.fromisoformat(run_metadata[key])
        except (TypeError, ValueError):
            raise ValueError(f"INVALID_INPUT: invalid {key}") from None
        _require(value.utcoffset() is not None, "RUN timestamps must have timezones")
        times.append(value)
    _require(times[1] >= times[0], "RUN end precedes start")
    diagnostics = result["diagnostics"]
    run = {**dict(run_metadata), **{k: diagnostics[k] for k in
           ("release_id", "condition_id", "method_id", "protocol_version", "status")},
           "input_sha256": diagnostics["input_sha256"],
           "configuration": diagnostics["matching_config"]}
    payloads = {
        "queries.csv": _csv_bytes(result["queries"], QUERY_FIELDS),
        "pairs.csv": _csv_bytes(result["pairs"], PAIR_FIELDS),
        "match_diagnostics.json": _encode_json(diagnostics),
    }
    run["output_sha256"] = {name: hashlib.sha256(blob).hexdigest()
                             for name, blob in payloads.items()}
    payloads["RUN.json"] = _encode_json(run)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, blob in payloads.items():
        with (output / name).open("xb") as stream:
            stream.write(blob)
    return run
