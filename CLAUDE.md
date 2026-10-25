# 主控交接

## HANDOFF

- 最终验收目标：复现并修复 PR #5 的三项 A 校验缺口，提交回归测试、更新同一 PR、逐条回复并请求 yibu1314 复审；分工由用户确认，B/C/D 算法与真实输入不变，不合并、不运行真实 FULL/矩阵（用户 2026-10-25 明确授权）。
- 当前：F-006三项缺口已复现并完成本地修复/回归；待精确发布、更新PR#5及回复/复审请求。打包修复2ed4e32、落盘身份修复476867d、manifest字节绑定修复b93de40；审查线程由审查人复核，尚未宣称通过。
- 科学运行：新 FULL 与矩阵 NOT_RUN。A 已复核历史输入；B 的 79508e3 分支已有匹配 API，专用测试/PR/CLI 接缝尚待完成；C/D 未见公开模块交付。不能把旧 HANDOFF 的未实现摘要当作 B 分支没有代码。
- 写域：仅本项目。旧来源只读；数据、参考、完整运行产物与本机发布配置不进入公共 Git。
- 协作：三位已加入仓库；yibu1314 已审查0010d6b并提交三条COMMENTED意见，未Approve；Issue #2现由pyy62300自assign但无认领说明，分工由用户另行确认，本轮不调整assignee。其他角色和进度以GitHub Issues为准。
- 实际检查：三个核心回归在旧生产代码上3失败（均DID NOT RAISE），修复后3通过；A全套109 passed/2 skipped（缺B后端），新增40回归。固定A实现b93de40与B 79508e3的人工检出111 passed；两种人工CLI各4查询/3接受、合成64查询/48候选通过。原输入/参考/交付18文件hash不变；没有真实FULL或矩阵。原件见.local/F006-reproduce、F006-A-full.xml、F006-integration/evidence.json。
- 公开协作：bootstrap c84275b 已公开，四 Issue 与 main 的 PR/非作者审查/fixture-tests 保护已生效。A 后续代码走 codex/preexp-data 和 PR，不直接推进 main；最新发布事实保存在本地精确发布记录与 GitHub。
- 输入：七份来源清单/所需载荷哈希与身份通过，64 对唯一参照、旧47对原距离/ratio与原8探针通过；原描述子字节不变，7候选名单固定。D 尚未独立复核。旧算法未复制；数组只作获准团队交付，匿名公开再分发未授权。
- 下一步：发布本轮精确提交，核验CI并在三个原审查线程回复修复/回归证据，再请求yibu1314复审；最新回读事实留.local/F006-completion.json及GitHub。分工由用户确认，不改Issue assignee或同学算法，不自行解决线程、批准或合并。
- 开工机器门禁：2026-10-23T13:33:38Z，PASS_WITH_NOTES；doctor/lease=0，verify/comms=1，保留全局既有备注。最终发布与收口机器记录留本地忽略目录。
- 交接门禁：2026-10-19T12:26:21Z，handover-check=PASS_WITH_NOTES；doctor=0、lease=0、verify=1、comms=1。全局既有投影/通信备注保留，不冒称全局 clean。机器原件在本地忽略目录 `.local/handover-check.json`；本机租约已登记。

快速检查见 README。此文件只摘要当前交接状态，不复制科学协议或 Issue 看板。公共 clone 无需维护者控制工具；本地 hooks 保持开启，后续公开发布仍需适用的精确授权。
