# 主控交接

## HANDOFF

- 最终验收目标：补齐 A 的条件/配置绑定、公共匹配入口、人工集成检查和新手 Git/PR 指南，更新现有 PR #5，供四人实际认领、审查和交付；真实输入不变，B/C/D 核心仍由同学维护，新 FULL/矩阵不运行（用户 2026-10-23 明确要求先完成 A 的补充）。
- 当前：正在执行 F-004（公共接口和协作入口补齐），预计约一小时；A_INTEGRATION_IN_PROGRESS。继续 codex/preexp-data，更新 PR #5，不直接合并 main。
- 科学运行：新 FULL 与矩阵 NOT_RUN。A 已复核历史输入；B 的 79508e3 分支已有匹配 API，专用测试/PR/CLI 接缝尚待完成；C/D 未见公开模块交付。不能把旧 HANDOFF 的未实现摘要当作 B 分支没有代码。
- 写域：仅本项目。旧来源只读；数据、参考、完整运行产物与本机发布配置不进入公共 Git。
- 协作：三位已加入仓库；yibu1314 有 B 分支交付证据，Issue 正式认领待补；另两位的 C/D 分工待本人确认。首轮工程审查按 B→A、C→B、D→C、A→D，D 的独立科学复核职责另保留。Issue 为唯一进度来源。
- 实际检查：50 tests passed；重新安装包到独立本地目录、从真实 ZIP 解包后，verify-inputs/verify-reference/status 均通过。五个 B/C/D/矩阵入口仍明确未实现。科研 payload 未进入 CI。
- 公开协作：bootstrap c84275b 已公开，四 Issue 与 main 的 PR/非作者审查/fixture-tests 保护已生效。A 后续代码走 codex/preexp-data 和 PR，不直接推进 main；最新发布事实保存在本地精确发布记录与 GitHub。
- 输入：七份来源清单/所需载荷哈希与身份通过，64 对唯一参照、旧47对原距离/ratio与原8探针通过；原描述子字节不变，7候选名单固定。D 尚未独立复核。旧算法未复制；数组只作获准团队交付，匿名公开再分发未授权。
- 下一步：完成 F-004 的兼容接口、CLI、验证及新手文档，使用固定 B 快照做人工接缝检查，再按原生发布机制更新同一 PR。B 自己补测试并提 Draft PR；不替 B 实现或提交核心算法，不改输入包或科研参数。
- 交接门禁：2026-10-19T12:26:21Z，handover-check=PASS_WITH_NOTES；doctor=0、lease=0、verify=1、comms=1。全局既有投影/通信备注保留，不冒称全局 clean。机器原件在本地忽略目录 `.local/handover-check.json`；本机租约已登记。

快速检查见 README。此文件只摘要当前交接状态，不复制科学协议或 Issue 看板。公共 clone 无需维护者控制工具；本地 hooks 保持开启，后续公开发布仍需适用的精确授权。
