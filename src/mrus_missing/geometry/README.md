# C 几何：US_TO_MR 刚体拟合

本目录由 C 维护，实现 PROTOCOL §6/§9 的刚体拟合。只读"已被 B 接受"的配对与两端坐标，**不读参考变换、不评分、不给真值**。

## 文件

| 文件 | 作用 |
|---|---|
| `rigid.py` | 秩判定、Kabsch/SVD 刚体解（强制 det(R)=+1）、残差与矩阵合法性 |
| `ransac.py` | PCG64 采样、内点判定、三档选优、一次重拟合与状态机 |
| `contracts.py` | 协议 v1 常量、状态名、`geometry` 配置块校验 |
| `io.py` | pairs/points CSV 读取、三个产物写出、`source_commit` |
| `__init__.py` | CLI 入口 `fit(pairs, mri_points, us_points, config, output)` |

## 输入与输出

- 输入 `pairs.csv`：B 的接受配对，需 `query_id`、`candidate_id`（其余列忽略、按文件顺序保留）。
- 输入 `mri_points.csv` / `us_points.csv`：`point_id,i,j,k`，单位 index_unit。
- 输入 `config`：`configs/experiment-v1.json`，`geometry` 块必须与协议 v1 **完全一致**，否则按输入错误拒绝（不改阈值、不回落默认值）。
- 输出（新建目录，已存在即拒绝，不覆盖历史运行）：
  - `transform.json`：`direction/unit/status/R/t/fit_config/pairs_sha256/source_commit`；失败时 `R,t` 为 `null`，**绝不用单位阵占位**。
  - `inliers.csv`：`query_id,candidate_id,inlier,residual`，顺序与输入 pairs 一致。
  - `fit_diagnostics.json`：采样统计、选优信息、最终内点与两端秩、残差摘要、状态细码。

## 算法（与协议逐条对应）

1. **采样**：`PCG64(seed=20261005)`，最多 256 次，每次抽 3 对不重复。
2. **秩**：中心化后 SVD，奇异值 **严格大于** `smax*max(n,3)*float64_eps` 才计数；秩 <2 的样本跳过（共线拒绝，共面非共线可用）。
3. **解算**：Kabsch/SVD，反射修正后 `det(R)=+1`；`t = c_mri - R c_us`。
4. **内点**：`‖R p_us + t - p_mri‖ ≤ 1.0`。
5. **选优**：内点数多 → 内点残差平方和小 → 最早样本（严格 `<` 比较，先到者胜）。
6. **重拟合一次**：只用胜出内点重解，然后对**全部**配对重算残差与内点，并重判两端秩。
7. **判成功**：最终内点 ≥4 且两端秩 ≥2 才 `SUCCESS`；否则按下表失败，不二次搜索抢救。

| 状态 | 触发条件 | 细码 |
|---|---|---|
| `SUCCESS` | 最终内点 ≥4、两端秩 ≥2 | — |
| `INSUFFICIENT_MATCHES` | 配对数 <3 | `TOO_FEW_PAIRS` |
| `INSUFFICIENT_MATCHES` | 最终内点 <4 | `INSUFFICIENT_INLIERS` |
| `DEGENERATE` | 全部样本秩 <2 | `ALL_SAMPLES_DEGENERATE` |
| `DEGENERATE` | 重拟合所用内点秩 <2 | `REFIT_DEGENERATE` |
| `DEGENERATE` | 最终内点集秩 <2 | `FINAL_RANK` |
| `NO_VALID_MODEL` | 预算内没有有效模型 | `NO_MODEL_IN_BUDGET` |
| `INVALID_INPUT` | 未知 ID、重复 query、非有限坐标、配置不符 | CLI 退出 2 |

`SUCCESS` 只说明数值条件成立；内点是残差标签，不是"配对正确"的科学标签。

## 两个可手算复核的案例

两个案例都用同一个真值：绕 z 轴 30°、`t=(1.5,-2.0,0.5)`，US 点取自 10–25 的 index 坐标。

**案例 1（成功）**：5 对里 4 对一致、第 5 对故意偏 9 个单位。

- 输出 `SUCCESS`，内点 4，`R` 与真值差 ~1e-15，`t=(1.4999999999999902, -2.000000000000014, 0.49999999999999645)`。
- 内点残差 ~4e-15；被排除的第 5 对残差 9.0。
- 为什么不是 5 个内点：偏移 9 ≫ 阈值 1.0，残差直接暴露。

**案例 2（证据不足）**：同样配置只保留 3 对一致配对。

- 输出 `INSUFFICIENT_MATCHES` / `INSUFFICIENT_INLIERS`，`R,t = null`。
- 为什么：3 点总能被某个刚体变换精确解释（三角形在 3D 中可翻转），但协议要求最终内点 ≥4；不足 4 时宁可失败也不报 `SUCCESS`。

复跑：

```powershell
.\.venv\Scripts\python.exe -m mrus_missing.cli fit --pairs <pairs.csv> --mri-points <mri_points.csv> --us-points <us_points.csv> --config configs\experiment-v1.json --output runs\fit-001
```

同一份输入与 seed 重跑，三个产物逐字节一致（`transform.json` 除 `source_commit` 外完全一致）。

## 测试覆盖（`tests/test_geometry.py`，15 项）

| 要求 | 测试 |
|---|---|
| 非零人工旋转平移回收 | `test_recovers_nonzero_rotation_and_translation` |
| 矩阵正交、det=+1、有限 | `test_transform_matrix_is_orthonormal_and_proper` |
| CLI 端到端与三文件 | `test_cli_fit_writes_three_artefacts` |
| 反射不被当成成功 | `test_rigid_fit_never_returns_a_reflection`、`test_reflected_correspondences_do_not_become_success` |
| 反射离群不计入内点 | `test_reflection_outliers_are_not_inliers` |
| 共线退化 | `test_collinear_points_are_degenerate` |
| 共面非共线可用 | `test_coplanar_but_not_collinear_is_accepted` |
| 不足 4 对 | `test_fewer_than_four_pairs_is_insufficient` |
| 最终重拟合后内点不足 | `test_three_consistent_pairs_among_outliers_is_insufficient` |
| 同 seed 可复现 | `test_same_seed_is_reproducible` |
| 未知 ID 拒绝 | `test_unknown_candidate_is_rejected` |
| 不覆盖既有输出 | `test_existing_output_directory_is_not_overwritten` |
| 配置块必须一致 | `test_geometry_block_must_match_protocol` |
| 内点不超阈值 | `test_inliers_never_exceed_threshold` |

## 与 A 的接口变动（需 A 确认）

`fit` 从"未实现占位"变为真实实现，因此 `tests/test_bootstrap.py` 中把 `fit` 当未实现的两处参数被移除（`test_production_shell_fails_without_reading_or_writing`、`test_cli_unimplemented_exit_and_no_outputs`）。`cli.py` 的 `status.fit_evaluate_matrix` 与 help 文案仍写 `NOT_IMPLEMENTED`，属 A 维护的公共接口，留待 A 更新。
