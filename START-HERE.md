# 同学从这里开始

这轮固定既有模型的描述子，只改变 US 候选集合。默认 7 条件 × MNN/MNN_RATIO，共 14 行；当前 A 的数据准备已完成，B/C/D 核心算法由认领同学实现，正式实验未运行。

## 先看自己的任务

| 任务 | 你实际要交什么 | 第一次开工 |
|---|---|---|
| [B 匹配 #2](https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot/issues/2) | 查询诊断、接受配对、匹配测试和解释 | 从少量人工向量实现 MNN/ratio 边界 |
| [C 几何 #3](https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot/issues/3) | US_TO_MR 变换或明确失败、内点、拟合测试和解释 | 用人工非零旋转平移与退化点集 |
| [D 独立评价 #4](https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot/issues/4) | 输入独立复核、逐查询评分、检查、案例与解释 | 从手算分类开始，并复核 A 的真实输入 |

在对应 Issue 留下本人 GitHub 用户名、认领角色、可用时间和首次交付日期。A 统一接口，模块内部问题由本人修复。当前尚未分配同学账号，不需要先等到有仓库写权限才能阅读和运行本地人工检查。

## 安装与第一条检查

Python 3.10–3.12，CPU 即可；无需 GPU、Torch、影像处理环境或维护者的 PCA 工具。

```sh
git clone --branch codex/preexp-data https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot.git
cd mr-us-candidate-missing-pilot
python -m venv .venv
```

Windows PowerShell：`.venv\Scripts\Activate.ps1`；Linux/macOS：`source .venv/bin/activate`。

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
mrus-missing status
mrus-missing inspect-fixture tests/fixtures/interface-v1.json
```

本阶段 A 交付位于 `codex/preexp-data` 分支，main 继续遵守 PR/非作者审查。看到 `NOT_RUN` 是准确的科研状态。`prepare/verify-inputs/verify-reference/package-inputs` 已实现；`match/fit/evaluate/summarize/run-matrix` 仍返回 `NOT_IMPLEMENTED`，这是要由各负责人完成的部分。

测试全部使用人工材料，CI 不接研究数据。`tests/test_preparation.py` 自己构造完整的人工来源，覆盖 A 的生产程序；里面的“47 对”只是测试规模约定，不是科研输出。

## 拿到真实输入后

A 已准备两个独立压缩包，指纹与验收范围见 [DATA-HANDOFF.md](DATA-HANDOFF.md)。科研数据不在公共 Git；由 A 通过获准的团队渠道交付。尚未收到包时可以先完成上面的人工开发，不要重新训练或自行替换其他数据。

- B/C/D 取得 `release-v1-inputs.zip`，解压到新目录 `data/inputs/release-v1/`。
- A/D 另外取得 `release-v1-reference.zip`，解压到新目录 `evaluation_reference/release-v1/`。
- 压缩包根部直接是文件，不再套一层同名目录；不要覆盖已有 release。

```sh
mrus-missing verify-inputs --release data/inputs/release-v1 --expected-sha256 18416259a7f7a66cbdf69826ebd190c6732d537e3f57a7a5569d3e2a8a68fe01
```

D 再运行：

```sh
mrus-missing verify-reference --release data/inputs/release-v1 --reference evaluation_reference/release-v1 --expected-sha256 0729460216a2babf3e7abe2240ec8adfbf9248950b9be1ce009f9f67f8c40629
```

命令验证哈希、字段、候选名单和来源连接；D 仍需自行检查参照和评分口径，不能把 A 程序的 PASS 当成自己的独立复核。

## 代码接入

B 可使用公共读取器，返回值没有坐标或答案，且读取器不会读取坐标载荷：

```python
from pathlib import Path
from mrus_missing.preparation import load_matching_inputs
inputs = load_matching_inputs(Path("data/inputs/release-v1"), "RAND_1")
# inputs["mri_descriptors"]: float32[64,512]
# inputs["us_descriptors"]: float32[48,512]，顺序仍沿原 US descriptor_row
# query_ids / candidate_ids / candidate_source_rows 供输出绑定
```

C 可使用 `load_geometry_points(Path("data/inputs/release-v1"))` 取得 `mri/us` 两个 ID→坐标字典；真实拟合必须等待 B 的接受配对，不能把最近候选直接当接受项。D 的独立参考文件只在评价包中。

公共接口位置为 `src/mrus_missing/preparation/`；本人算法写入 matching/geometry/evaluation 对应目录，完整规则见 [PROTOCOL.md](PROTOCOL.md)。读取器不实现任何匹配、拟合或评分算法。

## 第一次交付

使用本人分支（建议 B=`codex/preexp-matching`、C=`codex/preexp-geometry`、D=`codex/preexp-evaluation`），提交生产函数及人工测试，开 PR 并在任务 Issue 写明：输入版本、代码 commit、运行命令、检查结果、未完成项，以及一个本人能解释的案例。

main 要求非作者审查与 `fixture-tests` 通过。先用各自账号实际交接，再接通一个真实 FULL；正式矩阵保持未启动。不要把本轮 A 对旧 47 对的复验当作 B 已经完成新的 FULL 匹配。
