# 主控交接

## HANDOFF

- 正在执行 F-008（2026-10-28）：按用户“把1，2做了”审查 D PR #7，并处理 C/D 公共测试与 CLI 能力说明；预期交付可复跑的人工审查证据、A 公共接口修订及原 PR 更新。固定 C=e32129d、D=5782a33；不代写学生核心，不合并 PR，不运行真实 FULL/正式矩阵。开工 handover-check=PASS_WITH_NOTES（2026-10-28T12:28:19Z），doctor/lease=0，verify/comms 为既有备注；记录在本地忽略目录。

- 最终验收目标：保留已交付的F-006返修，按用户2026-10-25决定把认领说明统一为本人自行assign、群里同步，无A审批；PR仍须非作者审查与CI，源码/数据/具体分工不变，不合并。
- 当前：F-006已发布87e86dd，CI通过、三条回复和yibu1314复审请求已回读；F-007只同步认领流程文档与任务页。打包修复2ed4e32、落盘身份修复476867d、manifest字节绑定修复b93de40不变，审查结论待本人给出。
- 科学运行：新 FULL 与矩阵 NOT_RUN。A 已复核历史输入；B 的 79508e3 分支已有匹配 API，专用测试/PR/CLI 接缝尚待完成；C/D 未见公开模块交付。不能把旧 HANDOFF 的未实现摘要当作 B 分支没有代码。
- 写域：仅本项目。旧来源只读；数据、参考、完整运行产物与本机发布配置不进入公共 Git。
- 协作：三位已加入仓库；Issue #2由pyy62300自行assign已生效，无需A审批；用户在群里协调分工。其他成员同样自行认领，技术进展可后补；本轮不调整任何assignee，也不按reviewer推断模块角色。进度以GitHub Issues为准。
- 实际检查：三个核心回归在旧生产代码上3失败（均DID NOT RAISE），修复后3通过；A全套109 passed/2 skipped（缺B后端），新增40回归。固定A实现b93de40与B 79508e3的人工检出111 passed；两种人工CLI各4查询/3接受、合成64查询/48候选通过。原输入/参考/交付18文件hash不变；没有真实FULL或矩阵。原件见.local/F006-reproduce、F006-A-full.xml、F006-integration/evidence.json。
- 公开协作：bootstrap c84275b 已公开，四 Issue 与 main 的 PR/非作者审查/fixture-tests 保护已生效。A 后续代码走 codex/preexp-data 和 PR，不直接推进 main；最新发布事实保存在本地精确发布记录与 GitHub。
- 输入：七份来源清单/所需载荷哈希与身份通过，64 对唯一参照、旧47对原距离/ratio与原8探针通过；原描述子字节不变，7候选名单固定。D 尚未独立复核。旧算法未复制；数组只作获准团队交付，匿名公开再分发未授权。
- 下一步：发布F-007文档修订并同步Issue/PR的认领措辞；保留已有复审请求，不重复通知或改人员分配。F-006证据在.local/F006-completion.json，F-007回读在.local/F007-completion.json；不自行解决线程、批准或合并。
- 开工机器门禁：2026-10-23T13:33:38Z，PASS_WITH_NOTES；doctor/lease=0，verify/comms=1，保留全局既有备注。最终发布与收口机器记录留本地忽略目录。
- 交接门禁：2026-10-19T12:26:21Z，handover-check=PASS_WITH_NOTES；doctor=0、lease=0、verify=1、comms=1。全局既有投影/通信备注保留，不冒称全局 clean。机器原件在本地忽略目录 `.local/handover-check.json`；本机租约已登记。

快速检查见 README。此文件只摘要当前交接状态，不复制科学协议或 Issue 看板。公共 clone 无需维护者控制工具；本地 hooks 保持开启，后续公开发布仍需适用的精确授权。
