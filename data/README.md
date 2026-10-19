# 真实输入（本地管理）

`inputs/release-v1/` 及其内容被 Git 忽略。当前没有生成新科研 release。

需要 A/D 后续确认：两个 MODEL_TRAINED 描述子及原 row/ID、两份 PointSet、模型/checkpoint/preprocess 身份、旧 47 对、旧变换、独立参考及原 8 探针。旧记录和 manifest 可定位，存在不等于载荷已复验，也不等于有权分发。

当前盘点已定位两份描述子、两份 PointSet、旧 MatchSet/Transform 的 manifest 与载荷文件，以及独立参考文件。描述子和旧输出的 manifest SHA-256 与固定来源记录相符；载荷只检查存在，未加载或复验科研数组，未读取参考坐标/探针实物内容。新 release、逐载荷 hash、ID/row 语义、探针及共享许可仍待 A/D 完成。

旧项目整体算法复用许可未确认，研究派生数据共享许可待核实。未重编码、未评价，不可将旧数字复制为新结果。

文件合同见 PROTOCOL 第 2 节。复制 `configs/paths.example.toml` 为被忽略的 `paths.local.toml`，填本机相对路径或在私有配置中填写绝对路径。模块应使用明确参数；当前空壳不读取这些路径。后续实现可由 A 增加 `MRUS_DATA_ROOT` 解析，不能假装本版已支持。

先确认可共享成员、渠道和许可，再按源/输出 SHA-256 建只读 release。参考放独立本地目录，匹配入口不得读取。影像、权重、完整运行与个人路径不入公共仓。
