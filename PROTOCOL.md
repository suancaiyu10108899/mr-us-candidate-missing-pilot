# 候选缺失协议 v1.0

状态：协议 v1.0；A 已准备 release-v1 与固定候选名单，D 独立复核和正式共同代码冻结待完成；新 FULL/矩阵 NOT_RUN。
本文件是唯一科学定义，机器配置为 `configs/experiment-v1.json` 的对应表达。变更需说明依据、更新版本；不因已见结果调阈值或挑 seed。

## 1. 问题与边界

固定旧 MODEL_TRAINED 编码器的描述子，只改变 US 候选集合，研究有/无正确候选时的接受、拒绝、误接受和覆盖，并观察刚体拟合。先人工样例，再真实 FULL，再固定 14 行矩阵。

既有底座是单病例、已见位置、MRI 与合成 US、整数平移；历史报告 N=64、K=47、C=47。47/64 是筛选后的正确覆盖，不是未筛选 Top-1，也不是本轮结果。历史训练不计入四人本轮贡献。

删除向量只表示答案不在候选集合，保留块的纹理与描述子没有改变。不能外推到真实 FoV 裁剪、声影、切除、真实 US、跨患者泛化、毫米精度或临床 TRE。数组轴不是解剖方向；随机子集不是独立患者。原论文已涉及部分对应与筛选；本轮是本地流程诊断，不据此宣称文献空白。

本轮不重新训练/编码、运行影像处理/MMHVAE、换模型、加病例/噪声/旋转影像、搜索阈值或扩展平台。结果全好或无差异也可完成；不为创新故事制造坏例。

## 2. 输入、ID 与隔离

真实输入包 `data/inputs/release-v1/`：manifest.json、mri_descriptors.npy、us_descriptors.npy、mri_points.csv、us_points.csv、conditions.json。
独立参考 `evaluation_reference/release-v1/`：reference.json、correspondences.csv、baseline_pairs.csv、baseline_transform.json、input_audit.json、source_evidence.json、reference_manifest.json。

A 的 prepare/verify-inputs/verify-reference/package-inputs 已实现；新输入包额外保存 experiment.json、attribution.json。manifest 的逐文件 hash 与信封 content_sha256 分开，交接页另给完整 manifest 文件 SHA-256。文件名单封闭，额外文件也拒绝。包修改须新版本，不能替换旧 release。

manifest 至少记录 release_id/schema_version、固定源仓与 commit/运行、源与输出 SHA-256、encoder/checkpoint/preprocess 身份、dtype/shape、坐标单位、行序和转换步骤。未知字段留缺项，不猜 hash。新输入形成新 release，原 release 只读。

描述子保持 float32[64,512]；运算转 float64，不重新归一化。坐标为 float64[64,3] 的 IJK/index_unit。points 字段：point_id、descriptor_row（零基）、i、j、k、source_id。模态内 ID 唯一、row 完整覆盖 0–63；通过 row 绑定描述子，不依赖 CSV 显示顺序或两模态同 ID。禁止利用 ID 暗示答案。

A/D 检查文件/hash、有限值、向量范数 > 1e-12、模型身份一致、坐标与行序、候选名单互斥/完整。B 只接描述子、ID、候选名单；C 只接预测 pairs 与点坐标；只有 D 评分入口读取独立参考。此为接口约定隔离，不声称密码学隔离。

D 以原坐标及参考变换确认每个 MRI 查询恰有一个 US 候选满足参考误差 ≤ 0.5，且一对一。否则暂停正式矩阵，不能硬填 64 对或删 16 即缺 16。

参考方向 US_TO_MR：R_ref=I，t_ref=(-4,+3,-2)，单位 index_unit。数学列向量 `R @ p_us + t`，行数组 `points_us @ R.T + t`。A 已核对参考实物与原 8 探针，D 后续独立复核；理论参考与旧运行变换分别保存。

## 3. 固定条件

所有条件保留 64 个 MRI 查询。

| condition_id | US 候选 | 删除规则 |
|---|---:|---|
| FULL | 64 | 不删除 |
| RAND_1 | 48 | PCG64 seed 2026101001，删 16 |
| RAND_2 | 48 | PCG64 seed 2026101002，删 16 |
| RAND_3 | 48 | PCG64 seed 2026101003，删 16 |
| SPATIAL_I | 48 | I 坐标降序，取前 16 |
| SPATIAL_J | 48 | J 坐标降序，取前 16 |
| SPATIAL_K | 48 | K 坐标降序，取前 16 |

随机基底为 US 稳定 ID 升序，NumPy PCG64 无放回选 16 个索引；空间相同坐标按稳定 ID 升序。固定并保存实际保留/删除 ID、seed、生成规则和输入 hash。匹配时恢复 US 原来源行序，下游不重新抽样。

默认 7 条件 × MNN/MNN_RATIO = 14 行。只有在正式结果前经范围确认，才能缩为 FULL/RAND_1/SPATIAL_I × 两方法的 6 行；本版选择 14 行。

## 4. 匹配

普通 L2：float32 转 float64 后 `sqrt(sum((q-u)**2))`，不使用平方 L2。可缓存全矩阵，但绑定两个描述子 hash、dtype 和代码；删除后重新确定 nearest、second、mutual。

eps=1e-12。最近与次近距离差 ≤ eps 视为前向并列；反向有两个以上候选距最小值差 ≤ eps 视为并列。不使用默认相对 isclose 容差。这些数值规则已按旧固定源码只读核对；没有复制实现。

MNN：查询的唯一最近 US 候选，其在完整 64 个 MRI 查询中的唯一反向最近邻也为该查询时接受。MNN 最少 1 候选，ratio 只作诊断。反向查询集不因任何筛选缩小。

MNN_RATIO：在 MNN 上再要求 d1/d2 < 0.8；等于 0.8、d2 ≤ eps、最近并列均拒绝，最少 2 候选。没有反向 ratio。不存在的 d2/ratio 为 null，不填 0。

保留全部检查项，主要拒绝原因优先级：invalid → insufficient_candidates → forward_ambiguity → ratio（仅 MNN_RATIO）→ reverse_ambiguity → not_mutual。无效正式输入为 INVALID_INPUT，不能静默删除行。旧报告的 ratio 拒绝数不等于改用 MNN 后必然增加的接受数。

同条件 `accepted_pairs(MNN_RATIO) ⊆ accepted_pairs(MNN)`。加 ratio 同时可能损失正确覆盖与减少误接，precision 不保证提高。

## 5. 条件性保留性质

固定描述子、完整 MRI 查询和数值规则时，FULL 已通过 MNN_RATIO 的配对只要 US 候选保留，就仍是唯一前向最近，次近距离不减，反向关系不变，应继续接受。

仅当真实 FULL 经 D 确认原 47 对正确且唯一时，删 16 候选至少保留 31 对正确接受。检查具体存活 ID 集合，不能只看数量 ≥31；MNN 也应包含这些对。

以真实 FULL/MNN_RATIO 正确集合 S0 为锚，两方法均报告 anchor_removed、anchor_survived、anchor_lost、correct_outside_anchor。应有 removed+survived=47、lost=0、C=survived+outside。MNN 的 outside 可能在自身 FULL 中已存在，不一律称新增收益。

分别比较同条件两方法与同方法 FULL→删除条件。D 另诊断 FULL 的 US 反向最近邻正确/错误/并列数：若所有候选反向最近邻都正确，MNN 会结构性阻止无对应误接。未核实该前提不宣称成立；零误接不能单独证明临床拒绝可靠。

## 6. 刚体拟合

float64 RANSAC + SVD，US_TO_MR，禁止反射；每条件方法独立 PCG64 seed=20261005，最多 256 次、每次 3 对。pairs 按 MRI 原来源行序。中心化秩至少 2（共线拒绝、共面非共线可用）；奇异值严格大于 `smax * max(n,3) * float64_eps` 计入秩。

内点残差 ≤ 1.0 index_unit；最大内点数优先，再最小内点残差平方和，再最早样本。最佳集合重拟合一次，重新判最终内点与两端秩；至少 4 个最终内点且非退化才 SUCCESS。相同 pairs/次序/点/seed/配置的结果应在数值容差内相同。

状态至少 SUCCESS、INSUFFICIENT_MATCHES、DEGENERATE、NO_VALID_MODEL、INVALID_INPUT、ERROR；细状态如 INSUFFICIENT_INLIERS 必须映射解释。失败 R/t=null，不用单位阵占位。SUCCESS 只表示数值条件成立；内点不是正确标签。

旧核心函数尚无确认可复用许可，C 应独立实现或先完成许可审查；不绕旧高层合同把 MNN 伪装成 MNN_RATIO 输入。

## 7. 独立评价

`reference_pair_error = norm(R_ref @ p_us + t_ref - p_mri)`；正确接受要求 ≤0.5。禁止用预测变换或内点标签定义真值。

五类：correct_accepted（C）、wrong_present、rejected_present、accepted_absent、rejected_absent。计数闭合：N=N_present+N_absent=64；N_present=C+wrong_present+rejected_present；N_absent=accepted_absent+rejected_absent；K=C+wrong_present+accepted_absent；N=K+rejected_present+rejected_absent。MNN 的 K 不大于 US 候选数。

precision=C/K；coverage_present=C/N_present；false_accept_absent=accepted_absent/N_absent；acceptance_all=K/N；coverage_all=C/N。零分母 JSON 为 null、CSV 空、图表 NA；FULL 的 false_accept_absent 为 NA，全拒绝 precision 为 NA。运行错误不伪填零或当作拒绝。

几何评分使用原 8 个明确来源的 US 探针：`norm((R_pred @ p+t_pred)-(R_ref @ p+t_ref))`，报告 mean/median/max index_unit；无有效变换/参考为 NA。矩阵须有限且形状正确，`max_abs(R.T @ R-I) ≤ 1e-6`、`abs(det(R)-1) ≤ 1e-6`。矩阵合法不等于准确，内部拟合残差另列。

D 从少量真实原数组/坐标独立复算距离、ratio 和参考误差，不全盘信任上游自报数值。手算例（仅人工）：2 有对应、1 无对应，正确接受 1、无对应误接 1、有对应拒绝 1，则 precision=1/2、coverage_present=1/2、false_accept_absent=1、acceptance_all=2/3。

## 8. 文件与生产接口

所有输出通过同目录 RUN.json 绑定 run_id、release_id、condition_id、method_id、protocol_version、source_commit、输入 hash。RUN 还含运行者、命令/配置、依赖版本、带时区起止时间、状态及输出 hash。正式固定提交；dirty 运行只能 debug。每次新 run_id/attempt，不覆盖既有输出。

| 模块 | 输入（明确隔离） | 输出 |
|---|---|---|
| prepare | 原输入路径、配置 | 新只读 release；参考独立保存 |
| match | 描述子目录、候选名单、condition/method | queries.csv、pairs.csv、match_diagnostics.json |
| fit | pairs、两端 points、配置 | transform.json、inliers.csv、fit_diagnostics.json |
| evaluate | release、预测目录、独立参考 | query_evaluation.csv、metrics.csv、checks.json、selected_cases.json |
| summarize | metrics、逐 query 评价 | 报告 |

queries：condition_id/method_id/query_id/query_row、nearest_id/second_id/d1/d2/ratio、forward_unique/reverse_unique/mutual/ratio_pass、accepted/accepted_candidate_id/rejection_reason。正式每行 64 query；accepted=false 时 accepted_candidate_id 空，nearest 不能给 C 当接受配对。

pairs：condition_id/method_id/query_id/candidate_id/d1/d2/ratio，只含接受项，沿 MRI 来源顺序。match_diagnostics 不含真值。

transform：direction/unit/status/R/t/fit_config/pairs_sha256/source_commit。inliers 保存输入 pair ID、最终内点标志与预测残差；diagnostics 保存有效抽样、退化与最终状态。

query_evaluation 按 ID 接参考、候选存在性、参考误差、五类及 FULL 对照。metrics 每条件方法一行，含身份/状态、全部计数/比率、四项 anchor 分解、fit_status/inlier_count/三项 probe error 与来源指针。checks 保存身份、计数、子集、存活集合、矩阵与跨文件检查。失败行保留，未知量为空；匹配有效拟合失败仍保留匹配指标。

案例按条件表顺序、MNN→MNN_RATIO、query 原行序，每个实际出现类型取首例；另取参考误差最大错误接受作反例（同值取原行序）。不存在的类型写未观察到，不制造案例。

## 9. 测试与真实 FULL 门

A/D：ID 重复、row 缺失、模型错、非有限值、非法名单必须报错；点行打乱仍正确连接。B：互为最近邻/非 mutual/并列、ratio=0.8、d2=0、0/1 候选、删次近重算、删正确候选与存活集合。C：非零人工旋转平移、反射、共线/共面、不足 4 对、最终重拟合退化。D：全拒绝/FULL 零分母、混 run/hash、手算分类。集成：上游失败不可伪造完整结果。各人调用自己的实际生产实现；A 准备器已以人工来源测试并验收旧输入，B/C/D 算法测试待本人实现。

真实 FULL+MNN_RATIO 须：输入和旧产物身份核实；新旧 47 对 ID 集完全一致；D 独立得 N64/K47/C47；旧距离/ratio 可得字段按 atol=1e-10、rtol=1e-8 比较，缺项记未比较；新旧变换在原 8 探针最大作用差 ≤1e-5，并另报新变换相对参考误差；子集关系成立，所有文件 ID 贯通，无参考辅助预测。缺旧变换/探针时提出协议修订，不造旧证据。失败先查身份/排序/符号/版本，不能直接放宽容差。

通过后冻结输入 release/实际名单、协议、共同 commit 与配置，才可另行获准运行矩阵。每行保留错误/算法失败/NA，固定 seed 不择优。D 独立评分，非作者复核完整链，四人解释并交付后停止。
