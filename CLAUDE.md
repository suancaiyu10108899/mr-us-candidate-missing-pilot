# 主控交接

## HANDOFF

- 最终验收目标：复现并修复 PR #5 的三项 A 校验缺口，提交回归测试、更新同一 PR、逐条回复并请求 yibu1314 复审；分工由用户确认，B/C/D 算法与真实输入不变，不合并、不运行真实 FULL/矩阵（用户 2026-10-25 明确授权）。
- 当前：正在执行 F-006（打包路径、落盘 RUN 身份、manifest 字节指纹返修），预计45–60分钟；基线为已公开0010d6b，审查三线程未解决。先在隔离人工fixture复现，再修改A生产代码和A回归测试，原科研包只核哈希。
- 科学运行：新 FULL 与矩阵 NOT_RUN。A 已复核历史输入；B 的 79508e3 分支已有匹配 API，专用测试/PR/CLI 接缝尚待完成；C/D 未见公开模块交付。不能把旧 HANDOFF 的未实现摘要当作 B 分支没有代码。
- 写域：仅本项目。旧来源只读；数据、参考、完整运行产物与本机发布配置不进入公共 Git。
- 协作：三位已加入仓库；yibu1314 已审查0010d6b并提交三条COMMENTED意见，未Approve；Issue #2现由pyy62300自assign但无认领说明，分工由用户另行确认，本轮不调整assignee。其他角色和进度以GitHub Issues为准。
- 实际检查：A 分支69 passed/2 skipped（缺B后端的两项接缝）；与固定B 79508e3组成的本地人工检出71 passed。人工CLI两方法和合成release候选检查通过；旧B单候选ratio标志缺口被退出4明确拒收。旧真实输入/参考/交付18文件hash不变；没有真实FULL或矩阵。证据在 .local/F004-tests-final.xml 与 .local/F004-integration-location-final.json。
- 公开协作：bootstrap c84275b 已公开，四 Issue 与 main 的 PR/非作者审查/fixture-tests 保护已生效。A 后续代码走 codex/preexp-data 和 PR，不直接推进 main；最新发布事实保存在本地精确发布记录与 GitHub。
- 输入：七份来源清单/所需载荷哈希与身份通过，64 对唯一参照、旧47对原距离/ratio与原8探针通过；原描述子字节不变，7候选名单固定。D 尚未独立复核。旧算法未复制；数组只作获准团队交付，匿名公开再分发未授权。
- 下一步：按 records/F-006-review-fixes.md 的边界不变式复现、修复和验证；保留正常输入与固定B兼容性，形成精确发布提交后更新PR#5并逐条回复/请求复审。由审查者确认问题解决，不自行批准或合并。
- 开工机器门禁：2026-10-23T13:33:38Z，PASS_WITH_NOTES；doctor/lease=0，verify/comms=1，保留全局既有备注。最终发布与收口机器记录留本地忽略目录。
- 交接门禁：2026-10-19T12:26:21Z，handover-check=PASS_WITH_NOTES；doctor=0、lease=0、verify=1、comms=1。全局既有投影/通信备注保留，不冒称全局 clean。机器原件在本地忽略目录 `.local/handover-check.json`；本机租约已登记。

快速检查见 README。此文件只摘要当前交接状态，不复制科学协议或 Issue 看板。公共 clone 无需维护者控制工具；本地 hooks 保持开启，后续公开发布仍需适用的精确授权。
