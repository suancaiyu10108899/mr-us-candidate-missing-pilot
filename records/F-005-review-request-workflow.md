# F-005：落实认领与审查操作

- 日期：2026-10-23；服务 CLAUDE 当前验收目标，用户明确要求落实流程补充并提供群消息草稿。
- 范围：协作文档、开工页、PR 模板和现有 PR #5；正式请求 B（yibu1314）审查最新发布 head。群消息由用户审阅后手动发送。
- 改动：认领模板与 assignee/reviewer 区分；B 同步 A、nullable 生成与 writer 校验、专用测试；Draft 的临时 base、改 main 后复查和 Ready for review；最新 head 审查通知；本人登录/Approve/Merge。
- 一致性：README 的 B/C 工程审查角色与 CONTRIBUTING 保持一致；D 的独立评价仍保留。
- 验收：文档差异和链接检查；确认生产源码/测试/配置无改动及原输入18文件hash不变；发布后核对远端 head、CI 与 reviewer 请求。具体结果见本地 F005-completion.json 和 GitHub。
- 认领：发布前核对 B/C/D Issue 尚无认领留言，先保留待认领；收到本人留言后由 A 确认并 assign，不代填同学环境或数据验收结果。
- 边界：不代同学修算法或写数值测试，不替审查人批准，不合并 main，不运行新真实 FULL 或矩阵。历史 F-004 人工组合结果不冒充本轮新增算法验证。
