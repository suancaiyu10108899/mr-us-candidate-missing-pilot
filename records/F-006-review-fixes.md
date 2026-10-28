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

验收结果：

- 旧生产代码0010d6b：三项核心回归均实测DID NOT RAISE；危险release_id的两个ZIP实际出现在隔离临时交付目录之外。没有访问真实科研数组或参考作复现。
- 2ed4e32：统一安全release_id规则并检查解析后的ZIP目标；新增15用例，preparation模块37通过，包含安全名称、路径/类型拒绝及不覆盖对照。
- 476867d：落盘RUN与diagnostics对照请求及已核快照；新增21用例，包括5身份/状态字段在RUN、diagnostics及两者共同篡改的15种情况，坏结构/缺文件和CLI退出4。
- b93de40：manifest指纹绑定首次验证字节，结束时比较原字节；新增4用例覆盖纯空白/紧凑JSON以及带外部SHA/兼容入口。
- 最终A全套109 passed/2 skipped；三项核心复现由3失败转3通过。固定B 79508e3的隔离人工检出111 passed，两个4查询CLI各接受3对，合成64查询RAND_1接受48对。
- 18份原input/reference/delivery文件SHA不变，B/C/D核心和实验配置无改动。新测试验证A的边界，不代替学生数值测试或D独立科研评价。
- 三条讨论保持待复审；发布、CI、逐条回复和review request以PR的远端事实为准，不把本地通过写成已获Approve。
