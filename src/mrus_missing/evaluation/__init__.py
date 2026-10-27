"""D 的独立评价入口：唯一读取独立参考的模块。

预测目录约定
------------
``predictions`` 可以是单个 run 目录，也可以是包含多个 run 目录的父目录。
每个 run 目录必须有 ``RUN.json``、``queries.csv``、``pairs.csv``；拟合产物
``transform.json`` / ``inliers.csv`` / ``fit_diagnostics.json`` 可选，缺失时
相关指标写空值，不伪造。

产物（写入新的 ``output`` 目录，不覆盖已有运行）
------------------------------------------------
``query_evaluation.csv``  逐查询五类与参考误差
``metrics.csv``           每条件×方法一行
``checks.json``           身份、计数闭合、子集、锚点、矩阵、跨文件检查
``selected_cases.json``   按协议顺序取首例 + 最大误差错误接受
``RUN.json``              本次评价的身份、输入 hash 与输出 hash
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .scoring import (
    FIVE_CLASSES,
    anchor_decomposition,
    check_counts_closure,
    classify_query,
    count_classes,
    first_case,
    metrics_from_counts,
    reference_error,
    worst_wrong_acceptance,
)

METHODS = ("MNN", "MNN_RATIO")
MATRIX_TOLERANCE = 1e-6


# --------------------------------------------------------------------------
# 基础读写
# --------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: _csv_value(row.get(name)) for name in fields})


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return repr(value)
    return value


def _display(value: Any) -> str:
    if value is None or value == "":
        return "NA"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _json_safe(value: Any) -> Any:
    """NaN / inf 转 None，供 json.dump(allow_nan=False) 使用。"""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def _git_commit() -> str | None:
    import subprocess
    try:
        result = subprocess.run(["git", "-C", str(Path(__file__).resolve().parent),
                                 "rev-parse", "HEAD"], capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


# --------------------------------------------------------------------------
# 读取 release / reference / predictions
# --------------------------------------------------------------------------
def _load_points(path: Path) -> list[dict]:
    rows = []
    for row in _read_csv(path):
        rows.append({
            "point_id": row["point_id"],
            "descriptor_row": int(row["descriptor_row"]),
            "xyz": [float(row["i"]), float(row["j"]), float(row["k"])],
        })
    rows.sort(key=lambda item: item["descriptor_row"])
    if [r["descriptor_row"] for r in rows] != list(range(len(rows))):
        raise ValueError(f"{path.name}: descriptor_row 未覆盖 0..N-1")
    if len({r["point_id"] for r in rows}) != len(rows):
        raise ValueError(f"{path.name}: point_id 重复")
    return rows


def _load_release(release: Path) -> dict:
    manifest = _read_json(release / "manifest.json")
    conditions_doc = _read_json(release / "conditions.json")
    conditions = {item["condition_id"]: item for item in conditions_doc["conditions"]}
    mri = _load_points(release / "mri_points.csv")
    us = _load_points(release / "us_points.csv")
    return {
        "release_id": manifest["release_id"],
        "manifest_sha256": _sha256(release / "manifest.json"),
        "conditions_sha256": _sha256(release / "conditions.json"),
        "conditions": conditions,
        "mri": mri,
        "us": us,
        "us_xyz": {p["point_id"]: p["xyz"] for p in us},
    }


def _load_reference(reference: Path) -> dict:
    doc = _read_json(reference / "reference.json")
    if doc.get("direction") != "US_TO_MR":
        raise ValueError("reference direction 必须是 US_TO_MR")
    pairs = {}
    for row in _read_csv(reference / "correspondences.csv"):
        query_id, candidate_id = row["query_id"], row["candidate_id"]
        if query_id in pairs:
            raise ValueError(f"reference: query {query_id} 有多个对应")
        pairs[query_id] = candidate_id
    return {
        "R": [[float(x) for x in row] for row in doc["R"]],
        "t": [float(x) for x in doc["t"]],
        "tolerance": float(doc.get("correctness_threshold", 0.5)),
        "pairs": pairs,
        "probes": [[float(x) for x in row] for row in doc.get("probes_us", [])],
        "manifest_sha256": _sha256(reference / "reference_manifest.json"),
    }


def _discover_runs(predictions: Path) -> list[Path]:
    if (predictions / "RUN.json").is_file():
        return [predictions]
    runs = sorted({path.parent for path in predictions.rglob("RUN.json")})
    if not runs:
        raise ValueError(f"{predictions}: 没有找到 RUN.json")
    return runs


def _load_run(run_dir: Path) -> dict:
    run = _read_json(run_dir / "RUN.json")
    queries = _read_csv(run_dir / "queries.csv")
    pairs = _read_csv(run_dir / "pairs.csv")
    condition = run.get("condition_id")
    method = run.get("method_id")
    if method not in METHODS:
        raise ValueError(f"{run_dir.name}: 未知方法 {method!r}")
    if not condition:
        raise ValueError(f"{run_dir.name}: RUN.json 缺少 condition_id")
    # C 的产物可以平铺在 run 目录，也可以放在 run/fit/ 子目录
    fit_dir = run_dir / "fit"
    transform_path = run_dir / "transform.json"
    diag_path = run_dir / "fit_diagnostics.json"
    if not transform_path.is_file() and (fit_dir / "transform.json").is_file():
        transform_path = fit_dir / "transform.json"
        diag_path = fit_dir / "fit_diagnostics.json"
    return {
        "dir": run_dir,
        "run": run,
        "run_id": run.get("run_id", run_dir.name),
        "condition_id": condition,
        "method_id": method,
        "queries": queries,
        "pairs": pairs,
        "transform": _read_json(transform_path) if transform_path.is_file() else None,
        "fit_diagnostics": _read_json(diag_path) if diag_path.is_file() else None,
        "run_sha256": _sha256(run_dir / "RUN.json"),
    }


# --------------------------------------------------------------------------
# 校验
# --------------------------------------------------------------------------
def _validate_run(run: dict, release: dict, query_ids: list[str]) -> None:
    name = run["dir"].name
    if run["run"].get("release_id") != release["release_id"]:
        raise ValueError(f"{name}: release_id 与输入包不一致")
    if run["condition_id"] not in release["conditions"]:
        raise ValueError(f"{name}: 未知 condition_id {run['condition_id']}")
    if len(run["queries"]) != len(query_ids):
        raise ValueError(f"{name}: 查询数 {len(run['queries'])} != {len(query_ids)}")
    got = [q.get("query_id") for q in run["queries"]]
    if got != query_ids:
        raise ValueError(f"{name}: query 顺序/ID 与输入包不一致")
    for query in run["queries"]:
        if query.get("condition_id") not in (None, "", run["condition_id"]):
            raise ValueError(f"{name}: queries.csv 混入其它 condition")
        if query.get("method_id") not in (None, "", run["method_id"]):
            raise ValueError(f"{name}: queries.csv 混入其它 method")


def _run_accepted_set(run: dict) -> set:
    return {(row["query_id"], row["candidate_id"]) for row in run["pairs"]}


def _check_cross_file(run: dict) -> dict:
    accepted = {(q["query_id"], q["accepted_candidate_id"])
                for q in run["queries"] if _truthy(q.get("accepted"))}
    pairs = _run_accepted_set(run)
    problems = []
    if accepted != pairs:
        problems.append(f"queries.accepted 与 pairs.csv 不一致：多 {len(accepted - pairs)}，少 {len(pairs - accepted)}")
    return {"ok": not problems, "problems": problems}


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1")


# --------------------------------------------------------------------------
# 单 run 评分
# --------------------------------------------------------------------------
def _score_run(run: dict, release: dict, reference: dict) -> list[dict]:
    condition = release["conditions"][run["condition_id"]]
    keep = set(condition["keep_ids"])
    mri_xyz = {p["point_id"]: p["xyz"] for p in release["mri"]}
    row_of = {p["point_id"]: p["descriptor_row"] for p in release["mri"]}
    records = []
    for query in run["queries"]:
        query_id = query["query_id"]
        truth_id = reference["pairs"].get(query_id)
        present = truth_id in keep
        accepted = _truthy(query.get("accepted"))
        accepted_id = query.get("accepted_candidate_id") or None
        if accepted and not accepted_id:
            raise ValueError(f"{run['dir'].name}: {query_id} accepted 但没有 candidate_id")
        if not accepted:
            accepted_id = None
        accepted_error = None
        accepted_is_correct = False
        if accepted:
            if accepted_id not in release["us_xyz"]:
                raise ValueError(f"{run['dir'].name}: 未知候选 {accepted_id}")
            accepted_error = reference_error(release["us_xyz"][accepted_id], mri_xyz[query_id],
                                             reference["R"], reference["t"])
            accepted_is_correct = accepted_error <= reference["tolerance"]
        records.append({
            "condition_id": run["condition_id"],
            "method_id": run["method_id"],
            "query_id": query_id,
            "query_row": row_of[query_id],
            "accepted": accepted,
            "accepted_candidate_id": accepted_id,
            "accepted_is_correct": accepted_is_correct,
            "present": present,
            "reference_candidate_id": truth_id,
            "reference_error": accepted_error,
            "class": classify_query(present, accepted, accepted_is_correct),
            "rejection_reason": query.get("rejection_reason") or ("accepted" if accepted else None),
            "nearest_id": query.get("nearest_id") or None,
            "d1": _to_float(query.get("d1")),
            "d2": _to_float(query.get("d2")),
            "ratio": _to_float(query.get("ratio")),
        })
    return records


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


# --------------------------------------------------------------------------
# 拟合指标
# --------------------------------------------------------------------------
def _fit_metrics(run: dict, reference: dict) -> dict:
    transform = run["transform"]
    if transform is None:
        return {"fit_status": "NOT_PROVIDED", "inlier_count": None,
                "probe_mean": None, "probe_median": None, "probe_max": None,
                "matrix_valid": None}
    status = transform.get("status", "UNKNOWN")
    matrix_valid = None
    probes = reference["probes"]
    errors = []
    if status == "SUCCESS" and transform.get("R") is not None and transform.get("t") is not None:
        rotation = [[float(x) for x in row] for row in transform["R"]]
        translation = [float(x) for x in transform["t"]]
        matrix_valid = _matrix_valid(rotation, translation)
        if probes and matrix_valid:
            for probe in probes:
                mapped = [sum(rotation[i][j] * probe[j] for j in range(3)) + translation[i] for i in range(3)]
                truth = [sum(reference["R"][i][j] * probe[j] for j in range(3)) + reference["t"][i] for i in range(3)]
                errors.append(math.dist(mapped, truth))
    return {
        "fit_status": status,
        "inlier_count": _inlier_count(transform, run.get("fit_diagnostics")),
        "probe_mean": sum(errors) / len(errors) if errors else None,
        "probe_median": sorted(errors)[len(errors) // 2] if errors else None,
        "probe_max": max(errors) if errors else None,
        "matrix_valid": matrix_valid,
    }


def _inlier_count(transform: dict, diagnostics: dict | None) -> int | None:
    """C 的 inlier_count 在 fit_diagnostics.final_inlier_count；两种位置都接受。"""
    for value in (transform.get("inlier_count"),
                  (diagnostics or {}).get("final_inlier_count")):
        if value is not None:
            return int(value)
    return None


def _matrix_valid(rotation: list, translation: list) -> bool:
    import numpy as np
    R = np.asarray(rotation, dtype=np.float64)
    t = np.asarray(translation, dtype=np.float64)
    if R.shape != (3, 3) or t.shape != (3,):
        return False
    if not (np.isfinite(R).all() and np.isfinite(t).all()):
        return False
    return bool(np.abs(R.T @ R - np.eye(3)).max() <= MATRIX_TOLERANCE
                and abs(abs(np.linalg.det(R)) - 1.0) <= MATRIX_TOLERANCE)


# --------------------------------------------------------------------------
# 主入口
# --------------------------------------------------------------------------
def evaluate(release: Path, predictions: Path, reference: Path, output: Path) -> dict:
    """独立评分：只读独立参考，不采信上游自报的对错。"""
    output = Path(output)
    if output.exists():
        raise ValueError("output 已存在；每次评价用新的 run 目录")
    rel = _load_release(Path(release))
    ref = _load_reference(Path(reference))
    run_dirs = _discover_runs(Path(predictions))
    query_ids = [p["point_id"] for p in rel["mri"]]

    runs, keys = [], set()
    for run_dir in run_dirs:
        run = _load_run(run_dir)
        _validate_run(run, rel, query_ids)
        key = (run["condition_id"], run["method_id"])
        if key in keys:
            raise ValueError(f"重复的 run：{key[0]}/{key[1]}")
        keys.add(key)
        run["records"] = _score_run(run, rel, ref)
        run["metrics"] = _metrics_for(run, rel, ref)
        runs.append(run)

    anchor_run = next((r for r in runs if r["condition_id"] == "FULL" and r["method_id"] == "MNN_RATIO"), None)
    anchor = {(rec["query_id"], rec["accepted_candidate_id"]) for rec in anchor_run["records"]
              if rec["accepted"] and rec["accepted_is_correct"]} if anchor_run else None

    checks = _build_checks(runs, rel, ref, anchor, anchor_run)
    cases = _build_cases(runs, rel)

    output.mkdir(parents=True, exist_ok=False)
    query_rows = [rec for run in runs for rec in run["records"]]
    _write_csv(output / "query_evaluation.csv", query_rows, [
        "condition_id", "method_id", "query_id", "query_row", "accepted",
        "accepted_candidate_id", "present", "reference_candidate_id",
        "reference_error", "class", "rejection_reason", "nearest_id", "d1", "d2", "ratio",
    ])
    _write_csv(output / "metrics.csv", [run["metrics"] for run in runs], [
        "release_id", "condition_id", "method_id", "protocol_version", "status",
        "N", "N_present", "N_absent", "C", "wrong_present", "rejected_present",
        "accepted_absent", "rejected_absent", "K",
        "precision", "coverage_present", "false_accept_absent", "acceptance_all", "coverage_all",
        "anchor_total", "anchor_removed", "anchor_survived", "anchor_lost", "correct_outside_anchor",
        "fit_status", "inlier_count", "probe_mean", "probe_median", "probe_max",
    ])
    (output / "checks.json").write_text(
        json.dumps(_json_safe(checks), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (output / "selected_cases.json").write_text(
        json.dumps(_json_safe(cases), ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    manifest = {
        "schema_version": "evaluation-run-v1",
        "run_id": "evaluate-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "release_id": rel["release_id"],
        "protocol_version": "1.0",
        "source_commit": _git_commit(),
        "status": "EVALUATED_DEBUG",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "release_manifest_sha256": rel["manifest_sha256"],
            "release_conditions_sha256": rel["conditions_sha256"],
            "reference_manifest_sha256": ref["manifest_sha256"],
            "predictions": {run["run_id"]: run["run_sha256"] for run in runs},
        },
        "output_sha256": {name: _sha256(output / name) for name in
                          ("query_evaluation.csv", "metrics.csv", "checks.json", "selected_cases.json")},
    }
    (output / "RUN.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")

    return {
        "status": "EVALUATED_DEBUG",
        "release_id": rel["release_id"],
        "runs": len(runs),
        "queries": len(query_rows),
        "output": str(output),
        "checks_ok": checks["status"] == "PASS",
        "scientific_runs": "NOT_RUN",
    }


def _metrics_for(run: dict, release: dict, reference: dict) -> dict:
    condition = release["conditions"][run["condition_id"]]
    keep = set(condition["keep_ids"])
    counts = count_classes(rec["class"] for rec in run["records"])
    n_present = sum(1 for rec in run["records"] if rec["present"])
    n_absent = len(run["records"]) - n_present
    metrics = metrics_from_counts(counts, len(run["records"]), n_present, n_absent)
    metrics.update({"release_id": release["release_id"], "condition_id": run["condition_id"],
                    "method_id": run["method_id"], "protocol_version": "1.0"})
    fit = _fit_metrics(run, reference)
    metrics.update(fit)
    # FULL 不存在“正确候选缺席”的情形，误接受率记 NA
    if run["condition_id"] == "FULL" and n_absent == 0:
        metrics["false_accept_absent"] = None
    metrics["status"] = "EVALUATED"
    return metrics


def _build_checks(runs: list[dict], release: dict, reference: dict, anchor, anchor_run) -> dict:
    problems = []
    checks: dict = {
        "identity": {
            "release_id": release["release_id"],
            "release_manifest_sha256": release["manifest_sha256"],
            "reference_manifest_sha256": reference["manifest_sha256"],
            "runs": {f"{r['condition_id']}/{r['method_id']}": r["run_id"] for r in runs},
        },
        "counts_closure": {},
        "subset": {},
        "anchor": {},
        "matrix": {},
        "cross_file": {},
    }
    for run in runs:
        key = f"{run['condition_id']}/{run['method_id']}"
        m = run["metrics"]
        issues = check_counts_closure(
            {"correct_accepted": m["C"], "wrong_present": m["wrong_present"],
             "rejected_present": m["rejected_present"], "accepted_absent": m["accepted_absent"],
             "rejected_absent": m["rejected_absent"]},
            m["N"], m["N_present"], m["N_absent"])
        checks["counts_closure"][key] = {"ok": not issues, "problems": issues}
        problems.extend(f"{key}: {issue}" for issue in issues)
        checks["cross_file"][key] = _check_cross_file(run)
        if not checks["cross_file"][key]["ok"]:
            problems.extend(f"{key}: {p}" for p in checks["cross_file"][key]["problems"])
        if run["transform"] is not None and run["metrics"]["matrix_valid"] is False:
            problems.append(f"{key}: 变换矩阵不合法")
        checks["matrix"][key] = {"matrix_valid": run["metrics"]["matrix_valid"],
                                 "fit_status": run["metrics"]["fit_status"]}

    # 同条件 MNN_RATIO 的接受集合必须是 MNN 的子集
    by_condition: dict = {}
    for run in runs:
        by_condition.setdefault(run["condition_id"], {})[run["method_id"]] = run
    for condition, methods in by_condition.items():
        if "MNN" in methods and "MNN_RATIO" in methods:
            mnn = _run_accepted_set(methods["MNN"])
            ratio = _run_accepted_set(methods["MNN_RATIO"])
            extra = sorted(ratio - mnn)
            checks["subset"][condition] = {"ok": not extra, "extra": extra[:5]}
            if extra:
                problems.append(f"{condition}: MNN_RATIO 有 {len(extra)} 对不在 MNN 内")

    if anchor is None:
        checks["anchor"]["status"] = "NOT_AVAILABLE"
        checks["anchor"]["reason"] = "缺少 FULL/MNN_RATIO 运行"
    else:
        checks["anchor"]["total"] = len(anchor)
        for run in runs:
            key = f"{run['condition_id']}/{run['method_id']}"
            keep = set(release["conditions"][run["condition_id"]]["keep_ids"])
            accepted_ids = {(rec["query_id"], rec["accepted_candidate_id"])
                            for rec in run["records"] if rec["accepted"]}
            correct_ids = {(rec["query_id"], rec["accepted_candidate_id"])
                           for rec in run["records"] if rec["accepted"] and rec["accepted_is_correct"]}
            decomp = anchor_decomposition(anchor, keep, correct_ids, accepted_ids)
            checks["anchor"][key] = decomp
            run["metrics"].update({
                "anchor_total": decomp["anchor_total"],
                "anchor_removed": decomp["anchor_removed"],
                "anchor_survived": decomp["anchor_survived"],
                "anchor_lost": decomp["anchor_lost"],
                "correct_outside_anchor": decomp["correct_outside_anchor"],
            })
            if decomp["anchor_removed"] + decomp["anchor_survived"] + decomp["anchor_lost"] != len(anchor):
                problems.append(f"{key}: 锚点分解不闭合")
            if decomp["anchor_lost"] != 0:
                problems.append(f"{key}: 候选保留但锚对被拒 anchor_lost={decomp['anchor_lost']}")
    for run in runs:
        run["metrics"].setdefault("anchor_total", None)
        run["metrics"].setdefault("anchor_removed", None)
        run["metrics"].setdefault("anchor_survived", None)
        run["metrics"].setdefault("anchor_lost", None)
        run["metrics"].setdefault("correct_outside_anchor", None)

    checks["status"] = "PASS" if not problems else "FAIL"
    checks["problems"] = problems
    return checks


def _build_cases(runs: list[dict], release: dict) -> dict:
    order = {name: index for index, name in enumerate(release["conditions"])}
    ordered = sorted(runs, key=lambda r: (order.get(r["condition_id"], 999),
                                          METHODS.index(r["method_id"])))
    records = [rec for run in ordered for rec in run["records"]]
    cases = {}
    for case_type in FIVE_CLASSES:
        case = first_case(records, case_type)
        cases[case_type] = case if case is not None else {"observed": False}
    cases["worst_wrong_acceptance"] = worst_wrong_acceptance(records) or {"observed": False}
    return cases


# --------------------------------------------------------------------------
# 报告
# --------------------------------------------------------------------------
def summarize(metrics: Path, query_evaluation: Path, output: Path) -> dict:
    """把已验证的 metrics 与逐查询评价汇成 markdown 报告；不重新评分。"""
    metrics_path, query_path = Path(metrics), Path(query_evaluation)
    output = Path(output)
    if not metrics_path.is_file() or not query_path.is_file():
        raise ValueError("metrics 或 query_evaluation 不存在")
    rows = _read_csv(metrics_path)
    queries = _read_csv(query_path)
    output.mkdir(parents=True, exist_ok=True)
    lines = ["# 候选缺失预实验：评价摘要", "",
             f"- 行数（条件×方法）：{len(rows)}",
             f"- 查询记录：{len(queries)}", "",
             "| 条件 | 方法 | C | K | precision | coverage_present | false_accept_absent |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for row in rows:
        cells = [row.get("condition_id", ""), row.get("method_id", ""),
                 row.get("C", ""), row.get("K", ""),
                 _display(row.get("precision")), _display(row.get("coverage_present")),
                 _display(row.get("false_accept_absent"))]
        lines.append("| " + " | ".join(str(cell) for cell in cells) + " |")
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = {"status": "SUMMARIZED", "rows": len(rows), "queries": len(queries),
               "report": str(output / "report.md")}
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
