# 主控交接

## HANDOFF

- 最终验收目标：按用户 2026-10-28“把1，2做了”，完成 D PR #7 的实证审查，以及 C/D 公共测试、CLI 能力说明和人工组合验证；模块缺陷交原作者修复，不合并、不启动正式矩阵。
- 当前交付：F-008 的 A 公共实现为 d4c73b0；status/help 按当前 checkout 分别报告 B/C/D API，公共测试保留全部阶段并区分缺实现与无效输入。说明见 docs/MODULE-INTEGRATION.md，审查反例在 review_tests/。发布与 GitHub 审查的实际回读保存在本地忽略目录 .local/F008-completion.json（形成后）及 GitHub PR，不凭本摘要推断已经合并。
- 审查：固定 D=5782a33 原全套 121 passed/2 skipped；A 的人工审查正常对照 1 passed、16 个回归失败，归为 8 类身份/哈希、配对、拟合合法性、中位数与报告问题。固定 C=e32129d 在零接受 pairs 的公共接缝有 1 个失败，需由 C 修复；正常链通过不等于边界通过。
- 实际验证：A 全套 115 passed/4 skipped；A+C 130 passed/4 skipped；A+D 131 passed/4 skipped；A+B+C+D 隔离组合 150 passed，含两种方法的人工 match→fit→evaluate→summarize。未交付模块造成的 skips 如实保留，不把反例排除在默认 CI 的安排称为算法验收。原件在 .local/F008-review/，汇总在 .local/F008-validation.json。
- 版本与职责：B 的 79508e3 已有匹配 API，nullable ratio、专用测试与 PR 仍待本人；C/D 已有 PR #6/#7，不能再用“未实现骨架”概括各自分支。B=yibu1314、C=pyy62300、D=lil-wanglaoji 为 2026-10-28 Issue 快照，实际进度以 GitHub Issues 为准。本轮不调整 assignee、不代写核心。
- 既有 A 返修：F-006 的打包安全、落盘身份、manifest 原字节绑定修复保留；PR #5 仍待 yibu1314 复审。Issue 本人自行 assign、群内同步，无 A 审批；PR 仍须非作者批准、CI 和讨论处理，由本人执行 Approve/Merge。
- 科学状态：本轮 A 只执行 synthetic_fixture；真实 FULL 验收与正式矩阵未启动。C/D 曾报告真实输入本地 debug，不能笼统说全团队从未运行；其调试未独立验收。固定科研 input/reference/delivery 的 18 个文件哈希未变；不训练、不重新编码、不上传科研载荷。
- 写域：仅本项目的 A 公共代码、测试和文档；旧来源只读，main 与 B/C/D 分支不改。新实现继续经现有 A PR #5 交付，PUBLIC feature 发布仍须适用的 fresh exact grant 与原生 hooks。最新远端状态以本地发布回执和 GitHub 为准。
- 下一步：D 根据具体反例返修并补默认回归，C 修复空 pairs 的正常失败产物；同步 A 新公共测试，更新原 PR 再复审。B 本人工作并行继续。正式 FULL 和矩阵仍需后续明确启动，不以 CI 或 checks PASS 自动放行。
- 机器门禁：收口 handover-check=PASS_WITH_NOTES（2026-10-28T12:45:17Z），doctor/lease=0，verify/comms 为已有全局备注；收口卡在 .local/F008-handover.json。无需普通同学安装维护者控制工具。

快速入口见 README、START-HERE 与 docs/MODULE-INTEGRATION.md；逐项审查事实见 PR #6/#7 和 records/F-008-review-and-public-interfaces.md。
