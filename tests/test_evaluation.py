"""D 的评价模块测试：全部使用人工构造的小例子，不依赖科研数据。

覆盖协议要求：
  * 手算五分类例（2 有对应、1 无对应）
  * 零分母 / FULL 的 false_accept_absent = NA
  * 混 run / 错 release 拒收
  * MNN_RATIO ⊆ MNN 子集检查
  * 锚点分解（removed + survived + lost）
  * 首例选择与最大误差错误接受
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from mrus_missing.evaluation import evaluate, summarize
from mrus_missing.evaluation.scoring import (
    FIVE_CLASSES,
    anchor_decomposition,
    check_counts_closure,
    classify_query,
    count_classes,
    metrics_from_counts,
    reference_error,
)


# --------------------------------------------------------------------------
# 构造人工 release / reference / predictions
# --------------------------------------------------------------------------
def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_release(root: Path, conditions: dict, mri: list[tuple], us: list[tuple],
                 release_id: str = "synthetic-release") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({"release_id": release_id}), encoding="utf-8")
    (root / "conditions.json").write_text(json.dumps({"conditions": [
        {"condition_id": name, "keep_ids": keep} for name, keep in conditions.items()
    ]}), encoding="utf-8")
    for name, points in (("mri", mri), ("us", us)):
        _write_csv(root / f"{name}_points.csv", [
            {"point_id": pid, "descriptor_row": row, "i": xyz[0], "j": xyz[1], "k": xyz[2]}
            for row, (pid, xyz) in enumerate(points)
        ], ["point_id", "descriptor_row", "i", "j", "k"])
    return root


def make_reference(root: Path, pairs: list[tuple], probes: list[tuple] | None = None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "reference.json").write_text(json.dumps({
        "direction": "US_TO_MR", "correctness_threshold": 0.5,
        "R": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "t": [0.0, 0.0, 0.0], "probes_us": probes or [],
    }), encoding="utf-8")
    _write_csv(root / "correspondences.csv",
               [{"query_id": q, "candidate_id": c} for q, c in pairs],
               ["query_id", "candidate_id"])
    (root / "reference_manifest.json").write_text("{}", encoding="utf-8")
    return root


def make_run(root: Path, condition: str, method: str, accepted: dict,
             release_id: str = "synthetic-release") -> Path:
    """accepted: {query_id: candidate_id 或 None}。"""
    root.mkdir(parents=True, exist_ok=True)
    (root / "RUN.json").write_text(json.dumps({
        "run_id": f"{condition}-{method}", "condition_id": condition,
        "method_id": method, "release_id": release_id,
    }), encoding="utf-8")
    queries, pairs = [], []
    for row, (query_id, candidate_id) in enumerate(accepted.items()):
        entry = {
            "condition_id": condition, "method_id": method, "query_id": query_id,
            "query_row": row, "nearest_id": candidate_id or "", "second_id": "",
            "d1": "", "d2": "", "ratio": "", "forward_unique": "true",
            "reverse_unique": "true", "mutual": "true", "ratio_pass": "true",
            "accepted": "true" if candidate_id else "false",
            "accepted_candidate_id": candidate_id or "",
            "rejection_reason": "" if candidate_id else "not_mutual",
        }
        queries.append(entry)
        if candidate_id:
            pairs.append({"condition_id": condition, "method_id": method,
                          "query_id": query_id, "candidate_id": candidate_id})
    _write_csv(root / "queries.csv", queries, list(queries[0]))
    _write_csv(root / "pairs.csv", pairs, ["condition_id", "method_id", "query_id", "candidate_id"])
    return root


# --------------------------------------------------------------------------
# 纯函数
# --------------------------------------------------------------------------
def test_classify_query_five_classes():
    assert classify_query(present=True, accepted=True, accepted_is_correct=True) == "correct_accepted"
    assert classify_query(present=True, accepted=True, accepted_is_correct=False) == "wrong_present"
    assert classify_query(present=True, accepted=False, accepted_is_correct=False) == "rejected_present"
    assert classify_query(present=False, accepted=True, accepted_is_correct=False) == "accepted_absent"
    assert classify_query(present=False, accepted=False, accepted_is_correct=False) == "rejected_absent"


def test_reference_error_and_tolerance():
    R = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    t = [-4.0, 3.0, -2.0]
    err = reference_error([10.0, 10.0, 10.0], [6.0, 13.0, 8.0], R, t)
    assert err == pytest.approx(0.0, abs=1e-12)
    assert reference_error([0.0, 0.0, 0.0], [0.0, 0.0, 10.0], R, [0.0, 0.0, 0.0]) == pytest.approx(10.0)


def test_hand_example_metrics():
    """PROTOCOL §7 手算例：2 有对应、1 无对应 → precision=1/2。"""
    counts = count_classes(["correct_accepted", "rejected_present", "accepted_absent"])
    assert counts == {"correct_accepted": 1, "wrong_present": 0, "rejected_present": 1,
                      "accepted_absent": 1, "rejected_absent": 0}
    assert check_counts_closure(counts, n_total=3, n_present=2, n_absent=1) == []
    metrics = metrics_from_counts(counts, n_total=3, n_present=2, n_absent=1)
    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["coverage_present"] == pytest.approx(0.5)
    assert metrics["false_accept_absent"] == pytest.approx(1.0)
    assert metrics["acceptance_all"] == pytest.approx(2 / 3)
    assert metrics["coverage_all"] == pytest.approx(1 / 3)


def test_zero_denominator_is_none_not_zero():
    counts = count_classes(["rejected_absent"])
    metrics = metrics_from_counts(counts, n_total=1, n_present=0, n_absent=1)
    assert metrics["precision"] is None
    assert metrics["coverage_present"] is None
    assert metrics["false_accept_absent"] == pytest.approx(0.0)


def test_counts_closure_detects_break():
    counts = {name: 0 for name in FIVE_CLASSES}
    counts["correct_accepted"] = 2
    problems = check_counts_closure(counts, n_total=3, n_present=2, n_absent=1)
    assert problems  # 合计 2 != 3


def test_anchor_decomposition():
    anchor = {("q1", "u1"), ("q2", "u2"), ("q3", "u3")}
    decomp = anchor_decomposition(
        anchor,
        keep_ids={"u1", "u2"},             # u3 被删
        accepted_correct_ids={("q1", "u1")},
        accepted_ids={("q1", "u1")},
    )
    assert decomp == {"anchor_total": 3, "anchor_removed": 1, "anchor_survived": 1,
                      "anchor_lost": 1, "correct_outside_anchor": 0}


# --------------------------------------------------------------------------
# 端到端
# --------------------------------------------------------------------------
def build_case(root: Path, accepted_full: dict, accepted_rand: dict | None = None,
               release_id: str = "synthetic-release") -> tuple[Path, Path, Path]:
    release = make_release(
        root / "release",
        {"FULL": ["u1", "u2", "u3", "u4"], "RAND_1": ["u2", "u3", "u4"]},
        mri=[("q1", (0, 0, 0)), ("q2", (1, 0, 0)), ("q3", (2, 0, 0))],
        us=[("u1", (0, 0, 0)), ("u2", (1, 0, 0)), ("u3", (2, 0, 0)), ("u4", (5, 5, 5))],
        release_id=release_id,
    )
    reference = make_reference(root / "reference",
                               pairs=[("q1", "u1"), ("q2", "u2"), ("q3", "u3")],
                               probes=[(0, 0, 0)])
    preds = root / "preds"
    make_run(preds / "full_mnn", "FULL", "MNN", accepted_full, release_id=release_id)
    make_run(preds / "full_ratio", "FULL", "MNN_RATIO", accepted_full, release_id=release_id)
    if accepted_rand is not None:
        make_run(preds / "rand_mnn", "RAND_1", "MNN", accepted_rand, release_id=release_id)
        make_run(preds / "rand_ratio", "RAND_1", "MNN_RATIO", accepted_rand, release_id=release_id)
    return release, reference, preds


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_evaluate_hand_example_end_to_end(tmp_path):
    """RAND_1 删掉 u1：q1 误接 u2、q2 拒绝、q3 正确接受。"""
    release, reference, preds = build_case(
        tmp_path,
        accepted_full={"q1": "u1", "q2": None, "q3": None},
        accepted_rand={"q1": "u2", "q2": None, "q3": "u3"},
    )
    result = evaluate(release, preds, reference, tmp_path / "out")
    assert result["status"] == "EVALUATED_DEBUG"
    rows = read_csv(tmp_path / "out" / "metrics.csv")
    rand = next(r for r in rows if r["condition_id"] == "RAND_1" and r["method_id"] == "MNN_RATIO")
    assert rand["C"] == "1"
    assert rand["K"] == "2"
    assert float(rand["precision"]) == pytest.approx(0.5)
    assert float(rand["coverage_present"]) == pytest.approx(0.5)
    assert float(rand["false_accept_absent"]) == pytest.approx(1.0)
    assert float(rand["acceptance_all"]) == pytest.approx(2 / 3)


def test_full_false_accept_absent_is_na(tmp_path):
    release, reference, preds = build_case(
        tmp_path, accepted_full={"q1": None, "q2": None, "q3": None})
    evaluate(release, preds, reference, tmp_path / "out")
    rows = read_csv(tmp_path / "out" / "metrics.csv")
    assert all(r["false_accept_absent"] == "" for r in rows if r["condition_id"] == "FULL")
    checks = json.loads((tmp_path / "out" / "checks.json").read_text(encoding="utf-8"))
    assert checks["status"] == "PASS"


def test_wrong_release_is_rejected(tmp_path):
    release, reference, preds = build_case(
        tmp_path, accepted_full={"q1": "u1", "q2": None, "q3": None}, release_id="synthetic-release")
    # 篡改 run 的 release 身份
    run = preds / "full_ratio" / "RUN.json"
    data = json.loads(run.read_text(encoding="utf-8"))
    data["release_id"] = "another-release"
    run.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="release_id"):
        evaluate(release, preds, reference, tmp_path / "out")


def test_query_order_mismatch_is_rejected(tmp_path):
    release, reference, preds = build_case(
        tmp_path, accepted_full={"q1": "u1", "q2": None, "q3": None})
    path = preds / "full_mnn" / "queries.csv"
    rows = read_csv(path)
    rows[0], rows[1] = rows[1], rows[0]
    _write_csv(path, rows, list(rows[0]))
    with pytest.raises(ValueError, match="顺序"):
        evaluate(release, preds, reference, tmp_path / "out")


def test_ratio_not_subset_of_mnn_fails_check(tmp_path):
    release, reference, preds = build_case(
        tmp_path, accepted_full={"q1": "u1", "q2": None, "q3": None})
    # 让 MNN_RATIO 接受一个 MNN 没接受的配対（q2/u2，且是正确对）
    run = preds / "full_ratio"
    rows = read_csv(run / "queries.csv")
    rows[1]["accepted"] = "true"
    rows[1]["accepted_candidate_id"] = "u2"
    _write_csv(run / "queries.csv", rows, list(rows[0]))
    _write_csv(run / "pairs.csv", [{"condition_id": "FULL", "method_id": "MNN_RATIO",
                                    "query_id": "q2", "candidate_id": "u2"}],
               ["condition_id", "method_id", "query_id", "candidate_id"])
    evaluate(release, preds, reference, tmp_path / "out")
    checks = json.loads((tmp_path / "out" / "checks.json").read_text(encoding="utf-8"))
    assert checks["status"] == "FAIL"
    assert any("MNN_RATIO" in problem for problem in checks["problems"])


def test_anchor_removed_and_survived(tmp_path):
    release, reference, preds = build_case(
        tmp_path, accepted_full={"q1": "u1", "q2": None, "q3": None},
        accepted_rand={"q1": None, "q2": None, "q3": None})
    evaluate(release, preds, reference, tmp_path / "out")
    checks = json.loads((tmp_path / "out" / "checks.json").read_text(encoding="utf-8"))
    decomp = checks["anchor"]["RAND_1/MNN_RATIO"]
    assert decomp["anchor_total"] == 1
    assert decomp["anchor_removed"] == 1   # u1 被删
    assert decomp["anchor_lost"] == 0


def test_selected_cases_and_worst_error(tmp_path):
    release, reference, preds = build_case(
        tmp_path,
        accepted_full={"q1": "u1", "q2": None, "q3": None},
        accepted_rand={"q1": "u2", "q2": "u4", "q3": "u3"},
    )
    evaluate(release, preds, reference, tmp_path / "out")
    cases = json.loads((tmp_path / "out" / "selected_cases.json").read_text(encoding="utf-8"))
    assert cases["correct_accepted"]["query_id"] == "q1"   # FULL 的首例
    assert cases["accepted_absent"]["query_id"] == "q1"     # RAND_1 的首例
    assert cases["wrong_present"]["query_id"] == "q2"
    assert cases["worst_wrong_acceptance"]["query_id"] == "q2"
    assert cases["rejected_present"]["query_id"] == "q2"     # FULL 中 q2 被拒


def test_output_directory_must_be_new(tmp_path):
    release, reference, preds = build_case(
        tmp_path, accepted_full={"q1": "u1", "q2": None, "q3": None})
    (tmp_path / "out").mkdir()
    with pytest.raises(ValueError, match="已存在"):
        evaluate(release, preds, reference, tmp_path / "out")


def test_fit_diagnostics_supply_inlier_count(tmp_path):
    """C 的 inlier 数在 fit_diagnostics.json，不在 transform.json。"""
    release, reference, preds = build_case(
        tmp_path, accepted_full={"q1": "u1", "q2": None, "q3": None})
    run = preds / "full_ratio"
    (run / "transform.json").write_text(json.dumps({
        "direction": "US_TO_MR", "unit": "index_unit", "status": "SUCCESS",
        "R": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "t": [0.0, 0.0, 0.0],
    }), encoding="utf-8")
    (run / "fit_diagnostics.json").write_text(json.dumps({
        "status": "SUCCESS", "final_inlier_count": 2, "pair_count": 1,
    }), encoding="utf-8")
    evaluate(release, preds, reference, tmp_path / "out")
    rows = read_csv(tmp_path / "out" / "metrics.csv")
    ratio = next(r for r in rows if r["condition_id"] == "FULL" and r["method_id"] == "MNN_RATIO")
    assert ratio["fit_status"] == "SUCCESS"
    assert ratio["inlier_count"] == "2"
    assert float(ratio["probe_max"]) == pytest.approx(0.0, abs=1e-9)


def test_summarize_writes_report(tmp_path):
    release, reference, preds = build_case(
        tmp_path, accepted_full={"q1": "u1", "q2": None, "q3": None})
    out = tmp_path / "out"
    evaluate(release, preds, reference, out)
    summary = summarize(out / "metrics.csv", out / "query_evaluation.csv", tmp_path / "report")
    assert summary["rows"] == 2
    text = (tmp_path / "report" / "report.md").read_text(encoding="utf-8")
    assert "FULL" in text and "MNN_RATIO" in text
