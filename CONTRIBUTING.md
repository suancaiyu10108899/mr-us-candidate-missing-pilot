# 四人协作

任务认领、状态与交付链接统一在 [Issues](https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot/issues)。本文件只定义稳定职责，不维护第二份进度表。

| 角色 | 可改范围 | 建议分支 | 复核人 |
|---|---|---|---|
| A | preparation、公共 contracts/CLI/config、共同文档、整合 | `codex/preexp-data` | D（输入），另一成员（整合） |
| B | matching、`tests/test_matching.py` | `codex/preexp-matching` | D |
| C | geometry、`tests/test_geometry.py` | `codex/preexp-geometry` | A 或 B |
| D | evaluation、report、`tests/test_evaluation.py` | `codex/preexp-evaluation` | A，B/C 抽查 |

每人独立 clone 或 worktree，不共用可写 checkout。认领时填负责人、复核者、认领时间、可用时段和首次交付日期；B/C/D 未认领前不把 AI 补写登记为本人贡献。

先更新本地 main 并阅读最新公共接口，再开始自己的分支。接口变更先在 Issue 说明，由 A 统一维护；模块缺陷交回原负责人。仅 A 按已授权范围整合 main。

## PR 与验收

初始启动提交允许先发布再设置保护；此后 main 通过 PR 合并，至少一位非作者批准，`fixture-tests` CI 通过。作者不能自批；尚无合适复核者就等待认领，不绕过保护或伪造审查。

本机维护者的发布 hooks 按本仓精确可见性例外适配并持续启用；本机配置、授权文件及内部控制文档不公开。维护者后续 push 必须取得适用 exact 授权，不套用 PRIVATE 默认授权、不删除 hooks 或 `--no-verify`。普通同学独立 clone、各自账号、普通分支和 PR，无需安装维护者控制工具或 Windows 脚本。

PR 写清触发场景、结果变化、测试、输入/接口版本与已知限制。测试调用生产函数，不另写一套公式只测试自己。人工 fixture 与真实科研验收分别报告。CI 只使用仓内人工材料，不下载研究数组或请求研究数据凭据。

任务状态：待开始 → 进行中 → 已交付 → 已复核；受阻保留原因。交付不等于复核。人员缺席时由人决定延期、缩减或换人。

## 交付模板

在本人 Issue/PR 填写：任务 ID；负责人；输入 release 与 hash；代码 commit；命令/配置；产物位置与 hash；实际检查；未完成和已知问题；请求复核人；一个本人能解释的案例。真实路径只在获准的私有数据渠道传递。

B/C/D 分别交代码、实际产物和解释。D 从开始介入输入与评分；A 统稿并协调。每人用 3–5 分钟说明输入、一个计算、一个案例和一种失败。截图、AI 总结或 AI 之间意见一致不能替代证据。

不邀请未知账号，不共享凭据；不把原聊天、私人路径、研究数组或完整运行日志写进 Issues/PR。正式运行、额外训练和科学范围变化需另行确认；本轮骨架交付后停止。
