# C/D 接入与本轮审查交接

本页对应 A 的 F-008。C/D 的核心实现仍由本人维护；本轮只审查、修公共 CLI/测试并做人工组合验证，不合并 PR、不启动正式矩阵。

## 公共测试与 CLI 的处理

C/D 原先删除 `tests/test_bootstrap.py` 中已不适用的占位断言，理由成立。A 现已把这些测试改为按当前 checkout 的能力检验：

- 尚未交付的阶段：调用明确报 NOT_IMPLEMENTED，CLI 退出 3，不创建输出。
- 已交付的阶段：无效/不存在的输入明确报错，CLI 退出 2，不创建输出。
- `run-matrix` 保持未实现。普通 `status` 或 `--help` 不运行匹配、拟合、评分或读取输入包。

`status.stage_apis_in_this_checkout` 分别列出 match、fit、evaluate、summarize 等能力。旧的 `fit_evaluate_matrix` 合并字段已移除。子命令帮助也按实际后端显示，不再把已接入的 C/D 一起写成未实现。

这是结构能力发现，不是算法验收：`algorithm_acceptance=NOT_ASSESSED`，`scientific_run_history=NOT_INSPECTED`。C 的现有公开接口组合为 fit/fit_arrays/estimate；D 为 evaluate/summarize 以及导出的 classify_query/metrics_from_counts。A 用这些已交付接口区分实现与旧占位；将来接口变更先协调更新能力表，不能仅改状态文字。

## C/D 如何同步

在自己的分支先保存本人修改，再运行 `git fetch origin` 和 `git merge origin/codex/preexp-data`。A PR #5 未合 main 时，本人 PR 的 base 继续使用 `codex/preexp-data`。

若 `tests/test_bootstrap.py` 因原来的删项出现冲突，本轮约定采用 A 新版完整文件，保留所有按能力判断的公共测试；不要再次删除 fit/evaluate/summarize 的检查。仅对这个文件可执行：

```powershell
git restore --source=origin/codex/preexp-data --staged --worktree -- tests/test_bootstrap.py
```

这条命令会替换该文件，先确认其中没有尚未保存的本人新测试。其他冲突逐项判断，不把整个分支或本人算法覆盖成 A 版本。确认后运行公共测试、本人专用测试和全套 pytest，再完成 merge commit/push，原 PR 自动更新。

## 审查复现

固定审查版本：D PR #7 `5782a33`，C PR #6 `e32129d`。人工用例在 [review_tests](../review_tests/README.md)，所有输入由测试从零生成；不需科研数据包。

```powershell
python -m pytest tests/test_bootstrap.py tests/test_stage_capabilities.py -q
# D 在自己的实现上运行
python -m pytest review_tests/test_d_pr7_contract.py -q
# C 在自己的实现上运行
python -m pytest review_tests/test_c_empty_pairs.py -q
```

审查用例不在默认 `testpaths=tests` 中，因为 A 单独分支没有 C/D 实现，且现版学生代码确有未修问题。它们是需作者修复的明确失败证据，不是假装通过的 CI。修复后应把对应回归纳入本人默认测试并重新请求审查；不能通过跳过这些边界来验收。

A 另增加 `tests/test_module_integration.py`：实际 B/C/D 同时存在时，使用 A 从零生成的 synthetic_fixture 验证 match→fit→evaluate→summarize 两种方法的正常链路；缺模块时明确跳过。正常链路通过不能抵消审查反例失败。

## 仍需本人完成

- D：处理 PR #7 审查发现，保留独立输入/参考核验、预测产物绑定、矩阵合法性和报告不可覆盖等边界；补专用测试。
- C：有效的空 pairs（全部匹配被拒绝）应产生 INSUFFICIENT_MATCHES、R/t=null 等失败产物，不能被当成损坏 CSV。无表头/缺字段的坏文件仍应拒绝；还需正确构造 `(0,3)` 空点阵。
- B：自己的同步、nullable ratio、专用测试及 PR 工作不由本轮替代。

C/D 说明中已有的真实输入调试，须如实写“实际运行过调试、尚未经正式 FULL/矩阵验收”。不要用笼统的 NOT_RUN 覆盖已发生的调试，也不要把 checks PASS 或 CI 通过当作正式科学验收。
