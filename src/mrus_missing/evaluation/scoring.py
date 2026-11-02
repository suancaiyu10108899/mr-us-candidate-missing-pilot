"""D 的独立评分核心：纯函数，不读文件、不接触上游自报数值。

评分口径（PROTOCOL §7）：
    参考误差 = ||R_ref @ p_us + t_ref - p_mri||，<= 0.5 视为正确。
    五类：correct_accepted / wrong_present / rejected_present /
          accepted_absent / rejected_absent。
计数闭合：
    N        = C + wrong_present + rejected_present + accepted_absent + rejected_absent
    N_present= C + wrong_present + rejected_present
    N_absent = accepted_absent + rejected_absent
    K        = C + wrong_present + accepted_absent
    N        = K + rejected_present + rejected_absent
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

CORRECT_TOLERANCE = 0.5
FIVE_CLASSES = (
    "correct_accepted",
    "wrong_present",
    "rejected_present",
    "accepted_absent",
    "rejected_absent",
)


def reference_error(point_us: Sequence[float], point_mri: Sequence[float],
                    rotation: Sequence[Sequence[float]], translation: Sequence[float]) -> float:
    """||R @ p_us + t - p_mri||，float64。"""
    err = 0.0
    for i in range(3):
        mapped = sum(rotation[i][j] * float(point_us[j]) for j in range(3)) + float(translation[i])
        err += (mapped - float(point_mri[i])) ** 2
    return math.sqrt(err)


def classify_query(present: bool, accepted: bool, accepted_is_correct: bool) -> str:
    """按“正确候选是否在候选集合内”和“是否接受”划分五类。

    accepted_is_correct 只有 accepted=True 时才有意义：接受的那一对参考误差 <= 0.5。
    """
    if accepted:
        if accepted_is_correct:
            return "correct_accepted"
        return "wrong_present" if present else "accepted_absent"
    return "rejected_present" if present else "rejected_absent"


def count_classes(classes: Iterable[str]) -> dict:
    """五类计数，缺失类型补 0。"""
    counts = {name: 0 for name in FIVE_CLASSES}
    for name in classes:
        if name not in counts:
            raise ValueError(f"unknown class: {name}")
        counts[name] += 1
    return counts


def check_counts_closure(counts: dict, n_total: int, n_present: int, n_absent: int) -> list:
    """返回违反闭合关系的中文说明；空列表表示通过。"""
    problems = []
    total = sum(counts.values())
    if total != n_total:
        problems.append(f"五类合计 {total} != N {n_total}")
    if counts["correct_accepted"] + counts["wrong_present"] + counts["rejected_present"] != n_present:
        problems.append("P 类合计 != N_present")
    if counts["accepted_absent"] + counts["rejected_absent"] != n_absent:
        problems.append("A 类合计 != N_absent")
    if n_total != n_present + n_absent:
        problems.append("N != N_present + N_absent")
    return problems


def ratio_or_none(numerator: int, denominator: int) -> float | None:
    """零分母返回 None（JSON null / CSV 空），不填 0。"""
    if denominator == 0:
        return None
    return numerator / denominator


def metrics_from_counts(counts: dict, n_total: int, n_present: int, n_absent: int) -> dict:
    """由五类计数导出指标。FULL 的 false_accept_absent 由调用方置 None。"""
    correct = counts["correct_accepted"]
    wrong = counts["wrong_present"]
    rejected_present = counts["rejected_present"]
    accepted_absent = counts["accepted_absent"]
    rejected_absent = counts["rejected_absent"]
    accepted_k = correct + wrong + accepted_absent
    return {
        "C": correct,
        "wrong_present": wrong,
        "rejected_present": rejected_present,
        "accepted_absent": accepted_absent,
        "rejected_absent": rejected_absent,
        "K": accepted_k,
        "N": n_total,
        "N_present": n_present,
        "N_absent": n_absent,
        "precision": ratio_or_none(correct, accepted_k),
        "coverage_present": ratio_or_none(correct, n_present),
        "false_accept_absent": ratio_or_none(accepted_absent, n_absent),
        "acceptance_all": ratio_or_none(accepted_k, n_total),
        "coverage_all": ratio_or_none(correct, n_total),
    }


def anchor_decomposition(anchor: Iterable[tuple], keep_ids: set, accepted_correct_ids: set,
                        accepted_ids: set) -> dict:
    """以 FULL/MNN_RATIO 的正确接受集合为锚，分解到当前条件。

    anchor_removed : 锚对的 US 候选被删除（无法再接受）
    anchor_survived: 锚对候选仍在，且仍被同一对接受
    anchor_lost    : 锚对候选仍在，但当前没有被接受
    """
    removed = survived = lost = 0
    anchor_list = list(anchor)
    for qid, cid in anchor_list:
        if cid not in keep_ids:
            removed += 1
        elif (qid, cid) in accepted_ids:
            survived += 1
        else:
            lost += 1
    return {
        "anchor_total": len(anchor),
        "anchor_removed": removed,
        "anchor_survived": survived,
        "anchor_lost": lost,
        "correct_outside_anchor": len(accepted_correct_ids) - survived,
    }


def first_case(records: Sequence[dict], case_type: str) -> dict | None:
    """按给定顺序取该类型的首例；没有则返回 None（报告写“未观察到”）。"""
    for record in records:
        if record["class"] == case_type:
            return record
    return None


def worst_wrong_acceptance(records: Sequence[dict]) -> dict | None:
    """参考误差最大的错误接受；同值取查询原行序靠前者。"""
    candidates = [r for r in records
                  if r["accepted"] and not r["accepted_is_correct"] and r["reference_error"] is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda r: (r["reference_error"], -r["query_row"]))
