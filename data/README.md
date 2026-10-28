# 真实输入（本地管理）

`inputs/release-v1/` 及其内容被 Git 忽略。A 已生成并校验真实 release-v1；内容、指纹、接收角色和获取方式统一见 [DATA-HANDOFF.md](../DATA-HANDOFF.md)。

已经完成 A 的载荷/来源/ID/row/模型身份、唯一参照、旧 47 对与原 8 探针验收。D 尚须独立复核。本轮没有执行新的 FULL 匹配或矩阵。

描述子 NPY 原字节保留，坐标通过稳定 ID 绑定并保留 descriptor_row，候选名单按固定规则一次生成；下游直接读取名单，不重新抽样。prepare 不覆盖已有目录；verify-inputs 支持来自交接页的外部 manifest SHA-256。

真实包限制于已批准的团队交付，保留 ReMIND/CrossKEY 来源与局限；未公开再分发数组。旧算法没有复制，不把原仓软件许可与研究数据许可混为一谈。

文件合同见 PROTOCOL 第 2 节。程序使用明确 CLI/函数参数。`paths.example.toml` 只作本机路径记录示例，当前不自动解析该 TOML 或 MRUS_DATA_ROOT。

参考放独立目录与独立 ZIP。B 的 load_matching_inputs 读取描述子、候选名单及身份清单，不读取点坐标或参考载荷。影像、权重、完整运行与个人路径不入公共仓。
