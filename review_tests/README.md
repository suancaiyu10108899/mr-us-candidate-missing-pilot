# 人工审查反例

读者：正在返修 PR #6/#7 的 C/D 与复审者。这里只保存 A 的人工审查证据，不实现学生算法，不读取科研输入。默认 pytest 仍只收集 `tests/`。

在本人分支同步 A 后显式运行：

```powershell
python -m pytest review_tests/test_d_pr7_contract.py -q
python -m pytest review_tests/test_c_empty_pairs.py -q
```

请分别在 D/C 实现上执行。A 单独分支只有占位入口，不适用这些预期。

固定 D `5782a33`：原全套 121 passed / 2 skipped；本组 17 项中正常对照 1 passed，16 个回归失败，对应以下 8 类问题：

| 类别 | 复现现象 | 主要用例 |
|---|---|---|
| 输入与参考身份 | 改点坐标未更新 manifest、参考绑定另一个输入，仍检查通过 | changed_input_payload / reference_from_another_input_binding |
| 预测来源 | 改 queries 未更新 RUN hash，或 RUN 为 ERROR/错协议/错输入指纹，仍检查通过 | changed_prediction_payload / failed_or_mixed_prediction_identity |
| 配对有效性 | pairs 重复被 set 隐藏；接受本条件已删除的候选仍检查通过 | duplicate_pairs / candidate_outside_condition |
| 拟合来源 | transform/diagnostics 的 pairs_sha256 与实际 pairs 不符，仍参与评分 | fit_from_different_pairs |
| 几何合法性 | det=-1 的反射、SUCCESS 但 R=null、错误方向/单位未使检查失败 | invalid_successful_transform |
| 中位数 | 8 个探针取第 5 项，未平均第 4/5 项 | eight_probe_median |
| 报告覆盖 | 重复 summarize 覆盖已有 report.md | summary_does_not_overwrite |
| 报告混源 | metrics 为 FULL、query_evaluation 为 RAND_1，仍生成摘要 | summary_rejects_queries |

输入包与参考由 A 现有 `tests/test_preparation.py` 的人工 fixture 通过 prepare 生成，并先经 verify_inputs/verify_reference 验证；随后每个反例施加明确变更。预测表为人工构造的传输样例，不声称是正式匹配结果。矩阵和中位数测试独立计算预期值。

固定 C `e32129d`：header-only pairs.csv 代表有效的零接受数，现接口抛 ValueError，没有正常失败产物。本组 1 项失败；C 应同时处理 CSV 读取与空数组形状，并将回归纳入默认专用测试。

修复后把这些用例与本人更完整的测试一起纳入默认 CI，再请求复审。详细公共衔接见 [MODULE-INTEGRATION](../docs/MODULE-INTEGRATION.md)。
