# 四人协作

任务认领、状态与交付链接统一在 [Issues](https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot/issues)。本文件只定义稳定职责，不维护第二份进度表。

| 角色 | 可改范围 | 建议分支 | 复核人 |
|---|---|---|---|
| A | preparation、公共 contracts/CLI/config、共同文档、整合 | `codex/preexp-data` | B（工程审查）；D（输入独立复核） |
| B | matching、`tests/test_matching.py` | `codex/preexp-matching` | C（工程审查）；D（独立评价） |
| C | geometry、`tests/test_geometry.py` | `codex/preexp-geometry` | D |
| D | evaluation、report、`tests/test_evaluation.py` | `codex/preexp-evaluation` | A，B/C 抽查 |

首轮工程审查采用 B→A、C→B、D→C、A→D；实际人员在 Issue 认领后填写。审查者可以提出修改或批准，不预设必须通过。D 的输入与科学评价独立职责不因轮转而取消。

新手按 [Git/PR 操作指南](docs/GITHUB-WORKFLOW.md) 完成真实交付。开发可以交错进行：C 先做人工几何、D 先做输入复核和手算评价，不必等上游全部合并。

每人独立 clone 或 worktree，不共用可写 checkout。Issue 由本人自行 assign，并在群里同步分工，无需 A 审批。分支/commit、环境和数据校验、PR链接、计划和阻塞信息可随进展补充，不作为认领前置条件；未收到数据时如实注明。B/C/D 未认领前不把 AI 补写登记为本人贡献。

通常先更新本地 main 并阅读最新公共接口，再开始自己的分支。当前 A 准备器先交付在 codex/preexp-data；合入 main 前，请按 START-HERE 取得该分支，并从该固定交付提交建立本人本地工作分支，避免从旧 main 丢失输入读取器。正式 PR 的 base/head 由 A 确认；A 合入后统一更新共同基线。接口变更先在 Issue 说明，由 A 统一维护；模块缺陷交回原负责人。仅 A 按已授权范围整合 main。

## PR 与验收

初始启动提交允许先发布再设置保护；此后 main 通过 PR 合并，至少一位非作者批准，`fixture-tests` CI 通过。作者不能自批；尚无合适复核者就等待认领，不绕过保护或伪造审查。

本机维护者的发布 hooks 按本仓精确可见性例外适配并持续启用；本机配置、授权文件及内部控制文档不公开。维护者后续 push 必须取得适用 exact 授权，不套用 PRIVATE 默认授权、不删除 hooks 或 `--no-verify`。普通同学独立 clone、各自账号、普通分支和 PR，无需安装维护者控制工具或 Windows 脚本。

PR 写清触发场景、结果变化、测试、输入/接口版本与已知限制。先写并提交可复跑的专用测试，再由 CI 自动执行；CI 不会替你补测试。测试调用生产函数，不另写一套公式只测试自己。人工 fixture 与真实科研验收分别报告。CI 只使用仓内人工材料，不下载研究数组或请求研究数据凭据。

有可讨论实现即可开 Draft PR，测试未齐全就写明，不需要假装完成。达到审查条件后转 Ready for review，由作者或 A 在 Reviewers 选择约定账号并请求审查。返修在同一分支 commit/push，原 PR 自动更新；重新请求复核当前最新 head，通过后由 A 合并，必要时下游实际消费确认。首次协作中的登录、Approve 和 Merge 按操作指南由对应本人确认并操作。不要在整个任务尚含科学交付时用 Closes 自动关闭 Issue。

任务状态：待开始 → 进行中 → 已交付 → 已复核；受阻保留原因。交付不等于复核。人员缺席时由人决定延期、缩减或换人。

## 交付模板

在本人 Issue/PR 填写：任务 ID；负责人；输入 release 与 hash；代码 commit；命令/配置；产物位置与 hash；实际检查；未完成和已知问题；请求复核人；一个本人能解释的案例。真实路径只在获准的私有数据渠道传递。

B/C/D 分别交代码、实际产物和解释。D 从开始介入输入与评分；A 统稿并协调。每人用 3–5 分钟说明输入、一个计算、一个案例和一种失败。截图、AI 总结或 AI 之间意见一致不能替代证据。

不邀请未知账号，不共享凭据；不把原聊天、私人路径、研究数组或完整运行日志写进 Issues/PR。当前阶段完成输入与人工模块协作；新真实 FULL、正式矩阵、额外训练和科学范围变化需另行确认。
