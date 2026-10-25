# F-006：PR #5 三项审查返修

- 日期：2026-10-25；目标链：CLAUDE 当前验收目标；审查基线0010d6b。
- 用户授权：复现三项问题、修复A、补回归、更新现有PR、逐条回复并请求yibu1314复审；不改学生算法、分工或合并。
- 写域：A preparation/files/release/delivery、matching_runner、A对应测试及必要交接说明。
- 不变式1：危险或非字符串release_id在创建交付目录/ZIP前拒绝，最终ZIP路径必须位于指定输出目录；正常打包/解包/不覆盖仍通过。
- 不变式2：落盘RUN的release/condition/method/protocol/status与请求及diagnostics一致；缺字段、错误字段、坏结构或坏JSON均以BackendContractError拒收，不报告成功。
- 不变式3：matching request的verified manifest指纹只来自通过可信SHA检查的字节；读取中语义不变的空白改写也必须被拒绝，稳定输入正常通过。
- 测试先行：三个核心回归在旧生产代码上必须实测失败，确认正常对照，再分别修复；额外覆盖路径格式、单字段身份变更、诊断错位和异常分类。
- 人工隔离：仅使用tests自己构造的fixture和A的传输test double；B固定快照仅作隔离人工兼容检查，不修改或提交B代码，不接真实科研数组作匹配。
- 输入保全：原input/reference/delivery共18文件前后SHA一致，不重建数据包。
- 验收：定向回归、全套A测试、必要的固定B人工接缝、精确分支/CI、三条回复与复审请求的远端回读。
- 发布：仅codex/preexp-data和既有PR#5，走原生精确授权；不合并main，不关闭审查讨论、不替审查者Approve。
- 原始证据：本地忽略目录.local/F006-*；公开只提交合成回归及简明结果。
