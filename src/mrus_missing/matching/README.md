# B descriptor matching API

B 的描述子匹配 Python API 已实现；旧 `mrus-missing match` CLI 仍保留
`NOT_IMPLEMENTED` 行为，等待 A 统一调整公共 CLI、status/help 和 bootstrap 合同。
本提交不修改 preparation、geometry、evaluation、正式配置或协议。

## Public functions

从 `mrus_missing.matching` 导入：

| 函数 | 输入 | 输出 |
|---|---|---|
| `l2_distances` | 两个 float32 二维描述子数组和实验配置 | float64 普通 L2 距离矩阵 |
| `match_descriptors` | 当前描述子、query/candidate IDs、candidate source rows、condition/method/release 身份和配置 | `queries`、`pairs`、`diagnostics` dict |
| `match_inputs` | 公共 `load_matching_inputs` 返回的六字段 dict 和匹配配置 | 同上；校验 release-v1 完整查询集和维度 |
| `write_match_outputs` | 匹配结果、全新输出目录及显式运行元数据 | 四个协议文件及 RUN dict |

正式输入必须通过 A 的公共 loader 和交接 manifest hash 核验。
`match_inputs` 接收且仅接收 `mri_descriptors`、`us_descriptors`、`query_ids`、
`candidate_ids`、`candidate_source_rows`、`release_id`。小规模人工数组可使用
`match_descriptors`。B 不接收点坐标、参考对应、参考变换或几何拟合输出。

## Rules

科学定义以仓库根目录的 `PROTOCOL.md` 为准，数值从实验配置读取：

- 源数组保持 float32，先转 float64，再计算 `sqrt(sum((q-u)**2))`。
  不归一化，不使用平方 L2 或 cosine。
- 每次基于当前候选集重新确定 nearest、second 和 mutual，不缓存旧集合的结果。
- MNN 要求唯一前向最近，以及该候选在完整 MRI 查询集中的唯一反向最近。
  反向集合不因 ratio 或接受状态而缩小。
- MNN_RATIO 还要求至少两候选、`d2 > eps`、`d1/d2 < ratio_threshold`。
  当前协议 threshold=0.8，等号拒绝；eps=1e-12，没有反向 ratio。
- 前向最近和次近差不超过 eps 为并列；反向有多个查询距最小值不超过 eps
  为并列。并列不按 ID 或行号选接受配对。
- 拒因优先级遵循协议：invalid（整次调用抛出 INVALID_INPUT）→
  insufficient_candidates → forward_ambiguity → ratio（仅 MNN_RATIO）→
  reverse_ambiguity → not_mutual。
- 最近身份不唯一时 nearest/second ID 为 null，距离仍保留；最近唯一而次近
  身份并列时 second ID 为 null，d2 和 ratio 仍可用于诊断。
  `ratio_pass` 仅表示数值 ratio 判据；接受还必须满足 unique/mutual。
- 零或近零范数、非有限值、非法 dtype/维度/ID/行绑定使整次调用失败，不能静默删行。

## Minimal artificial example

在仓库根目录、已安装 `.[dev]` 的受支持 Python 环境运行：

```python
import json
from pathlib import Path
import numpy as np
from mrus_missing.matching import match_descriptors

config = json.loads(Path("configs/experiment-v1.json").read_text(encoding="utf-8"))
result = match_descriptors(
    np.array([[10, 0]], dtype=np.float32),
    np.array([[14, 0], [15, 0]], dtype=np.float32),
    ["qA"], ["uX", "uY"], [0, 1],
    condition_id="SYNTHETIC", method_id="MNN_RATIO",
    release_id="synthetic-v1", config=config,
)
assert result["queries"][0]["ratio"] == 0.8
assert result["queries"][0]["rejection_reason"] == "ratio"
assert result["pairs"] == []
```

此例只使用人工描述子。qA 的 d1=4、d2=5，因此 MNN 接受，MNN_RATIO 拒绝。

## Output contract

`queries.csv` 为每个 query 保留一行，包含 nearest/second、d1/d2/ratio、
forward_unique/reverse_unique/mutual/ratio_pass、accepted 与 rejection_reason。
拒绝时 `accepted_candidate_id` 为空，nearest 仅作诊断。

`pairs.csv` 恰好包含 accepted=true 的 query/candidate 映射，沿 MRI 来源行序，
字段为 condition_id、method_id、query_id、candidate_id、d1、d2、ratio。
C 只能使用这些接受配对；不能把 tentative nearest 当作接受项。

`match_diagnostics.json` 记录身份、配置、维度/dtype、完整反向查询数量、候选
source-row 绑定和输入内容 hash，不含真值。描述子内容 hash 绑定 dtype/shape/
C-order bytes，US hash 对应当前选中子集；它不是源 NPY 文件或交接 manifest 的 hash。

`RUN.json` 绑定 run/release/condition/method、协议版本、source commit、输入和输出
hash、运行者、命令、配置、依赖版本、带时区起止时间与状态。writer 只写全新目录，
即使已有目录为空也拒绝覆盖。调用者须提供真实 commit/dirty 状态和唯一 run_id；
dirty 只能 debug。writer 不代替 A 的正式运行授权、Git 冻结或来源审查。

## Validation and integration status

B 专用人工测试、独立 oracle 和 mutation 审计曾在本地执行；其源码和临时产物
随后按用户要求清理，未纳入本提交。因此历史测试总数不代表当前检出的测试数量，
本分支不提供可复现的 B 专用测试套件。

本次发布前已执行仓库仍保留的 `python -m pytest -q`，结果为 **50 passed**。
这些测试覆盖公共准备器、
接口和 bootstrap 合同，不能替代 B 算法独立复核。正式集成前应补齐可复现的 B 测试，
并由 A 协调 CLI 合同、由非作者复核。

真实 FULL、固定 14 行矩阵、reference evaluation 和 geometry fitting 均未由 B 启动。
本提交不发布真实输入、真实配对、运行产物、本机路径或私人准备报告。
