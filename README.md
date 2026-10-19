# MR–US 候选缺失预实验

固定既有单病例合成 US 的描述子，只删除 US 候选，比较 MNN 与 MNN_RATIO 的接受、拒绝和误接受，并观察对刚体拟合的影响。

**当前仅完成启动骨架：科学运行 NOT_RUN，算法入口明确返回 NOT_IMPLEMENTED。** 人工样例只用于字段和接口互通；测试通过不代表研究结果成立。

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
git clone https://github.com/suancaiyu10108899/mr-us-candidate-missing-pilot.git
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

`prepare / match / fit / evaluate / summarize / run-matrix` 已有命令帮助和接口，但现在调用会以退出码 3 返回 `NOT_IMPLEMENTED`，不创建结果。`inspect-fixture` 仅验证人工接口材料的结构及 ID/row 绑定；不进行匹配、拟合或科学计分。

## 数据与流程

默认矩阵为 7 条件 × 2 方法，共 14 行。顺序为人工接口 → 各模块人工算法测试 → 真实 FULL 对齐 → 固定矩阵 → 独立复核。后三步尚未授权启动。

- `configs/experiment-v1.json`：候选协议数值配置，正式输入尚未冻结。
- `tests/fixtures/`：从零构造的 `synthetic_fixture`；不是研究数据。
- [data/README.md](data/README.md)：真实输入清单、许可与本地路径约定。
- `evaluation_reference/`：本地独立参考；`runs/`：完整本地运行输出。
- `results/verified/`：只接收另经审查允许发布的结果，目前为空。
- [CONTRIBUTING.md](CONTRIBUTING.md)：写域、PR、复核与交付模板。
- [CLAUDE.md](CLAUDE.md)：当前交接摘要；Issues 是唯一任务进度来源。

公开仓只承载新代码、协议和人工样例。真实描述子、坐标、参考、影像、权重及完整输出通过许可允许的独立渠道管理。仓库公开不授予研究数据分发权。

本实验不是临床验证、跨患者泛化或真实组织缺失实验。旧报告中的 47/64 是历史筛选覆盖，仅作为未来 FULL 对齐目标，不是本轮新结果。

## 许可

[MIT LICENSE](LICENSE) 覆盖本仓自有代码、文档及人工样例；维护者发布 hooks 按本项目范围改编自维护者自有模板，来源见其说明。未复制旧项目算法或第三方实现；未来复用须先核对具体文件许可并保留来源。研究输入不包含在该许可中。
