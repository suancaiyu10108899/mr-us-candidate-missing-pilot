# 人工接口材料

`interface-v1.json` 完全从零构造，kind=synthetic_fixture，scientific_result=false；维度和点数刻意不同于真实 64×512 输入。

当前 `inspect-fixture` 只检查结构、有限性、row/ID 和候选分区。`manual_geometry` 给 C 一个非零旋转/平移的手算目标；`manual_scoring` 给 D 手算分类目标。它们是未来算法测试的 oracle，当前未通过任何拟合或评分实现。B 的向量例子可供初次人工互通；完整数值边界测试由 B 另补。

不得把 fixture 放入真实 release 或正式 14 行表。未来真实 release 读取器必须明确拒绝该 kind。
