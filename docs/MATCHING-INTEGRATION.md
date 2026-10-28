# A/B 匹配接口与接入合同

这是公共接口的补充说明，不改变 PROTOCOL v1.0 的候选、阈值、几何或评分定义。release-v1 文件和两个 ZIP 不变。

## 分工与兼容

- B 维护 `matching` 中的数值算法、诊断和四文件 writer，提交自己的 `tests/test_matching.py`。
- A 维护输入读取、公共 CLI、运行身份和接口测试。
- `load_matching_inputs` 继续返回原六字段，不增加字段破坏 B `match_inputs` 的严格检查。
- 官方调用链新增 `load_matching_request`：一起返回六字段 inputs、condition_id、method_id、已验证 config、kind 和 provenance。公共 runner 从同一请求取得所有标签与配置。

六字段为 mri_descriptors / us_descriptors / query_ids / candidate_ids / candidate_source_rows / release_id。B 仍只接收这些字段和确定的 condition/method/config，不读取坐标或参考。

## 输入与来源绑定

`load_matching_request(release, condition_id, method_id, expected_sha256)` 要求交接页的完整 manifest 文件 SHA-256。它验证清单、描述子/条件/配置载荷哈希、固定 v1 参数、条件名称、FULL=64/删除条件=48、候选分区与来源行序。

解析配置和数组使用通过哈希检查的同一份字节；不从另一个文件重复读取后直接信任。匹配请求不读取坐标载荷或评价参考。A 的完整 `verify-inputs` 仍负责按坐标复核空间删除；收件人先完成该验证，再使用交接指纹匹配。

manifest 同样保留首次通过可信 SHA 检查的字节快照；读取结束时逐字节比较，纯空白或序列化格式变化也会拒绝。verified manifest 指纹来自该已验证快照，不以解析对象相等代替文件哈希相等。

低层 B API 可服务小型人工例子，调用者仍须遵守合同。正式输入应经 A 的绑定入口；不要手工把 RAND_1 的数组传成 FULL。公共 runner 还会核对 B 返回的条件、方法、release、数量、查询 ID/顺序和配置，错误时在 writer 前拒绝。

RUN/diagnostics 的 input_sha256 增加 A 的 verified_release_manifest_file、verified_conditions_file、verified_experiment_file、verified_condition_selection。它们是文件/名单指纹，与 B 原有数组内容 hash 分开，字段名不能互相冒充。

writer 完成后，A 回读 RUN 和 diagnostics，按绑定请求核对 release_id、condition_id、method_id、protocol_version 和 SUCCESS 状态，再核对已验证 diagnostics 快照、运行元数据、配置、完整输入指纹和三个 payload 的哈希。落盘身份错位、缺字段、坏 JSON 或缺文件均返回 BACKEND_CONTRACT_ERROR，不报告匹配完成；失败输出保留供排查，下次使用新的输出目录。此项验证错误 writer 的拒收语义，不表示 B 的正常 writer 已出现这些错误。

## 未定义 ratio

| 情况 | ratio | ratio_pass |
|---|---|---|
| 有可计算 ratio，且小于0.8 | 实际数值 | true |
| 有可计算 ratio，且不小于0.8 | 实际数值 | false |
| 没有次近候选，或 d2 ≤ eps | null | null |

这落实协议中未定义诊断为 NA 的约定。MNN 的接受不取决于 ratio_pass；MNN_RATIO 仍要求判据为 true。拒绝原因优先级不变。

B 需要同步自身记录生成器和 writer 的 nullable 校验，并提交边界测试。A 不重算或偷偷改写 B 的结果；不符合约定的旧结果会明确拒收。旧 B 79508e3 的单候选例子仍返回 false，是待 B 修复项。

## CLI 与运行状态

`status` 仅报告当前 checkout 的 API 可用性，不扫描运行历史，不表示科研通过。A 分支只有公共 runner 时，match/match_fixture 为 false；合入 B API 后为 true，算法验收仍显示 NOT_ASSESSED。

`match-fixture` 是第一次接入建议使用的人工命令（要在包含 A 更新和 B 实现的分支运行）：

```powershell
.\.venv\Scripts\python.exe -m mrus_missing.cli match-fixture --fixture tests/fixtures/interface-v1.json --config configs/experiment-v1.json --method-id MNN_RATIO --output runs/b-fixture-001 --run-id b-fixture-001 --operator YOUR_GITHUB_LOGIN
```

成功应为 MATCH_COMPLETED_DEBUG、kind=synthetic_fixture、4 个查询/3 个接受配对，并产生 queries.csv、pairs.csv、match_diagnostics.json、RUN.json。再次使用同一输出目录会被拒绝；下一次用新 run_id/目录。

`match` 已从原先的分散路径占位参数改为整包入口；运行一次明确指定的 debug 匹配：

```text
match --release <输入目录> --condition-id <固定条件> --method-id <MNN或MNN_RATIO>
      --expected-sha256 <交接manifest文件SHA> --output <新的runs目录>
      --run-id <唯一ID> --operator <运行者> [--input-kind research_input|synthetic_fixture]
```

公共入口不提供 formal 模式，也不启动矩阵。真实 FULL 当前仍未执行，后续由 A 统一接通。不能把人工命令成功当成真实47对对齐。

通过 editable Git checkout 执行：runner 检查 A/B 代码来自同一工作副本，自动记录实际 HEAD、dirty 标志与源码指纹，不接受手填的假 commit。dirty 运行仍明确为 debug。输出不得覆盖已有目录或写入只读输入包。

A 分支缺少 B 后端时，退出码3并返回明确的 B_matching_backend_in_current_checkout 未实现状态，不创建结果。输入/配置错误退出2；B 返回不合约的身份或诊断时退出4、状态 BACKEND_CONTRACT_ERROR，不能把它当作输入包坏了或一次正常拒绝。旧 Python `matching.match(...)` 占位函数暂保留兼容，公共 CLI 不再调用它。

## 测试责任

A 的测试覆盖绑定、配置、CLI 调用、来源传播和拒收语义；传输 test double 不运行数值匹配。含 B API 时，A 的两项真实人工接缝测试会运行；A 分支缺 B 时会明确 skipped。

B 的数值边界、候选删除、集合关系、writer 一致性等必须由 B 专用测试覆盖。CI 只运行已经提交的测试；A 接缝测试、历史本地测试叙述、评审临时脚本，都不能替代 B 自己的可复跑测试交付。
