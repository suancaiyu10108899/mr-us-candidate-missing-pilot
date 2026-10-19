# F-002：精确项目公开发布门禁

- 日期：2026-10-19；目标链：CLAUDE 本轮公开骨架目标。
- 必要性：维护者原模板只接受 PRIVATE；本项目获用户批准公开，需要精确适配而非关闭 hook。
- 来源：维护者自有 Python 项目模板 pre-push rev7；不修改全局模板或控制工具。
- 仅变更本仓可见性逻辑：精确仓库首次 CREATE_INITIAL_REF 要求 live private，后续 UPDATE_FF/CREATE_REF 要求 live public；其他对象或未知状态拒绝。
- 禁止 visibility/provider 环境覆盖；原生 publisher-check 与 R1–R6/P1 出站对象扫描保持，扫描段逐文本比对一致。
- 本机配置持续启用 core.hooksPath=.githooks。普通同学不必安装本机管理工具；PR+非作者审查+fixture CI 是公共协作入口。
- 实际测试：生产 PowerShell 函数的 3 个允许、7 个拒绝条件通过；原生 hook 缺 exact grant 时阻断。没有用模拟 provider 进行真实发布。
- 完整首发将由 fresh grant 绑定下列实际 hash，远端 equality/consume 后另行改变可见性；当前尚未声称首发完成。
- 初始源 pre-push.ps1 SHA-256：eae58e57f1a251eea8436b311b04dc1d84369258898cf747a2c2be161256d643。
- 变更记录由本提交的 Git diff 提供，敏感授权及日志只在本地忽略目录或仓外。

| 文件 | 实际 SHA-256 |
|---|---|
| commit-msg | `575bb1e02c377809da5776bf8e09ae462404923109f7cb2c6b9cfd8c2e604c24` |
| pre-push | `9bc5eb7b857f5c41f14f95d363d7fc25071ff90c97f8205e26bed1b867f3ce00` |
| pre-push.ps1 | `db4d551d8dcdbaa35b5b2503c796214c338ae063c61f3fb7d0929f8070103c4d` |
