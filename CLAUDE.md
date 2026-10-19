# 主控交接

## HANDOFF

- 最终验收目标：完成 A 当前可独立交付的旧产物复核、可重复数据准备程序、可验真的输入包及同学开工入口；B/C/D 核心算法留给同学，正式矩阵不运行（用户本轮明确要求）。
- 当前：F-003 的 A 准备器、真实 release-v1、两份独立交付包与开工说明已完成本地验收；A_PREPARED / D_REVIEW_PENDING。开发分支 codex/preexp-data，旧来源只读。代码协作入口见 START-HERE，包指纹见 DATA-HANDOFF。
- 科学运行：新 FULL 与矩阵 NOT_RUN。A 只复核历史产物，B/C/D 由真实同学认领，核心算法仍未实现。
- 写域：仅本项目。旧来源只读；数据、参考、完整运行产物与本机发布配置不进入公共 Git。
- 协作：A 为用户（数据与整合）；B 匹配、C 几何、D 独立评价待认领。Issue 为唯一进度来源。
- 实际检查：50 tests passed；重新安装包到独立本地目录、从真实 ZIP 解包后，verify-inputs/verify-reference/status 均通过。五个 B/C/D/矩阵入口仍明确未实现。科研 payload 未进入 CI。
- 公开协作：bootstrap c84275b 已公开，四 Issue 与 main 的 PR/非作者审查/fixture-tests 保护已生效。A 后续代码走 codex/preexp-data 和 PR，不直接推进 main；最新发布事实保存在本地精确发布记录与 GitHub。
- 输入：七份来源清单/所需载荷哈希与身份通过，64 对唯一参照、旧47对原距离/ratio与原8探针通过；原描述子字节不变，7候选名单固定。D 尚未独立复核。旧算法未复制；数组只作获准团队交付，匿名公开再分发未授权。
- 下一步：完成 A 分支的受控代码发布/PR入口；用户可转发 START-HERE 给同学了解和认领。成员账号/交付渠道明确后传递真实包，D复核输入，B/C/D各自开发。自动邀请暂缓，等待用户提供白名单；不自行启动新 FULL、矩阵或替代同学实现。
- 交接门禁：2026-10-19T12:26:21Z，handover-check=PASS_WITH_NOTES；doctor=0、lease=0、verify=1、comms=1。全局既有投影/通信备注保留，不冒称全局 clean。机器原件在本地忽略目录 `.local/handover-check.json`；本机租约已登记。

快速检查见 README。此文件只摘要当前交接状态，不复制科学协议或 Issue 看板。公共 clone 无需维护者控制工具；本地 hooks 保持开启，后续公开发布仍需适用的精确授权。
