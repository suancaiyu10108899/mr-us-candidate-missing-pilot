# MR–US 候选缺失预实验

固定既有单病例合成 US 的描述子，只删除 US 候选，比较 MNN 与 MNN_RATIO 的接受、拒绝和误接受，并观察对刚体拟合的影响。

**A 的数据准备与真实输入包已完成生产者验收；B/C/D 核心算法待同学实现，新 FULL 与正式矩阵仍为 NOT_RUN。** 从 [同学开工入口](START-HERE.md) 开始；真实输入的内容、指纹与获取方式见 [DATA-HANDOFF.md](DATA-HANDOFF.md)。

## 给同学的第一步

1. 阅读本页与 [公共协议](PROTOCOL.md)。
2. 在 [GitHub Issues](https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot/issues) 认领本人任务，填写可用时间与复核人。
3. 运行下面的人工样例检查，再从本人模块和测试开始。A 负责公共接口；B/C/D 各自实现核心工作。

| 角色 | 工作 | 起点 | 交付给谁 |
|---|---|---|---|
| A（用户） | 输入、协议与整合 | `src/mrus_missing/preparation/` | B/C/D，D 复核输入 |
| B（待认领） | 描述子匹配 | `src/mrus_missing/matching/` | C 与 D，D 复核 |
| C（待认领） | US_TO_MR 刚体拟合 | `src/mrus_missing/geometry/` | D，A 或 B 复核 |
| D（待认领） | 独立评分与解释 | `src/mrus_missing/evaluation/` | A，B/C 抽查 |

## 快速开始

Python 3.10–3.12，CPU 即可。骨架本地检查使用 Python 3.11.9、NumPy 1.26.4、pytest 9.1.1。

```sh
git clone --branch codex/preexp-data https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot.git
cd mr-us-candidate-missing-pilot
python -m venv .venv
```

Windows PowerShell 激活：`.venv\Scripts\Activate.ps1`；Linux/macOS：`source .venv/bin/activate`。

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
mrus-missing status
mrus-missing inspect-fixture tests/fixtures/interface-v1.json
mrus-missing --help
```

本地已有 pytest 时可直接 `python -m pytest -q`。未安装包时，PowerShell 可设 `$env:PYTHONPATH='src'` 后运行 `python -m mrus_missing.cli status`；POSIX 用 `PYTHONPATH=src python -m mrus_missing.cli status`。

`prepare / verify-inputs / verify-reference / package-inputs` 已实现，可整理固定旧产物、校验和打包。`match / fit / evaluate / summarize / run-matrix` 保留给后续负责人，调用仍以退出码 3 返回 `NOT_IMPLEMENTED`。`inspect-fixture` 只检查人工接口。

维护者已有获准的旧项目副本时，可重复准备到两个全新目录：

```sh
mrus-missing prepare --source OLD_PROJECT --config configs/experiment-v1.json --output data/inputs/release-v1 --reference-output evaluation_reference/release-v1
mrus-missing verify-inputs --release data/inputs/release-v1
mrus-missing verify-reference --release data/inputs/release-v1 --reference evaluation_reference/release-v1
mrus-missing package-inputs --release data/inputs/release-v1 --reference evaluation_reference/release-v1 --output .local/delivery/release-v1
```

`OLD_PROJECT` 是实际旧项目根目录的占位符；同学使用已交付包即可，无需访问旧私有仓。已有输出会被拒绝，重建使用新目录。程序不读取影像或权重，不运行新匹配/拟合/评分。

## 数据与流程

默认矩阵为 7 条件 × 2 方法，共 14 行。顺序为人工接口 → 各模块人工算法测试 → 真实 FULL 对齐 → 固定矩阵 → 独立复核。后三步尚未授权启动。

- `configs/experiment-v1.json`：协议数值配置；`source-crosskey-v1.json` 锁定来源清单。release-v1 的实际候选名单已生成，正式矩阵的共同代码版本仍未冻结。
- `tests/fixtures/`：从零构造的 `synthetic_fixture`；不是研究数据。
- [data/README.md](data/README.md)：真实输入清单、许可与本地路径约定。
- `evaluation_reference/`：本地独立参考；`runs/`：完整本地运行输出。
- `results/verified/`：只接收另经审查允许发布的结果，目前为空。
- [CONTRIBUTING.md](CONTRIBUTING.md)：写域、PR、复核与交付模板。
- [CLAUDE.md](CLAUDE.md)：当前交接摘要；Issues 是唯一任务进度来源。

公开仓只承载代码、协议、人工样例与不含载荷的交付指纹。真实描述子、坐标和参考独立打包，由 A 通过获准渠道交付；当前不提供匿名科研数组下载。仓库公开不授予研究数据分发权。

本实验不是临床验证、跨患者泛化或真实组织缺失实验。旧报告中的 47/64 是历史筛选覆盖，仅作为未来 FULL 对齐目标，不是本轮新结果。

## 许可

[MIT LICENSE](LICENSE) 覆盖本仓自有代码、文档及人工样例；维护者发布 hooks 按本项目范围改编自维护者自有模板，来源见其说明。未复制旧项目算法或第三方实现；未来复用须先核对具体文件许可并保留来源。研究输入不包含在该许可中。
