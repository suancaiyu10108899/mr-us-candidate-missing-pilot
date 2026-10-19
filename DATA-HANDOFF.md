# release-v1 输入交付

状态：A_PREPARED / D_REVIEW_PENDING / NEW_FULL_NOT_RUN / MATRIX_NOT_RUN。
这是 A 对旧产物的整理和生产者验收，不是新算法结果。输入包已在维护者本地生成；本页只公开元数据、指纹和获取方式，不公开科研数组。

## 两个包

| 包 | 接收角色 | 字节数 | SHA-256 |
|---|---|---:|---|
| release-v1-inputs.zip | B/C/D | 256522 | `4ad5e85ef82ed4d7c4012d7c3163a26d9fc72927fc4541df409bdc192c40eb40` |
| release-v1-reference.zip | A/D | 9933 | `f62acb44cb55076c0094a91804e9414c8af1baa2e372561c1454dcd4ae171399` |

- 输入 manifest 文件 SHA-256：`18416259a7f7a66cbdf69826ebd190c6732d537e3f57a7a5569d3e2a8a68fe01`。
- 参考 manifest 文件 SHA-256：`0729460216a2babf3e7abe2240ec8adfbf9248950b9be1ce009f9f67f8c40629`。
- 代码源码身份同时记录在输入 manifest 的 `preparation_source_hashes`；源科研身份绑定旧科学提交与原载荷 hash。

获取：认领者向 A 取得本人所需包，确认接收账号和获准渠道后传递。仓库链接可以直接转给同学查看和做人工开发；真实输入不附在公开 Issues/PR 或公开 Release。当前没有匿名科研数据下载地址。

输入包包含两份原字节不变的 float32[64,512] 描述子、两份按 ID/descriptor_row 绑定的点表、7 个固定候选名单、实验配置、来源说明和 manifest。评价包包含独立参考、64 对参照对应、旧 47 对、旧变换、原 8 探针、A 验收与来源清单。没有原影像、权重、整块影像、完整旧日志或私人机器路径。

## 已完成的 A 检查

- 七份来源 manifest 的文件 SHA-256 与固定旧记录相符，信封内容 hash 自洽。
- 两描述子 MODEL_TRAINED/encoder/checkpoint/preprocess 相容；PointSet/frame/父链一致。
- 载荷 SHA-256、大小、dtype/shape、有限值与非零向量通过；两份描述子 NPY 原字节保留。
- 通过稳定 ID 连接描述子与坐标，CSV 的显示行序不作为身份。
- 64 个查询均有且仅有一个参考对应，形成一对一关系。
- 旧 47 对逐项复核：原距离、次近距离和 ratio 的最大数值差为 0；检查对象只限历史接受配对，没有预测其余查询。
- 原 8 探针已恢复；旧变换相对参考的最大作用差为 `6.550880341146756e-14 index_unit`。这是旧变换检查，不是新拟合结果。
- 固定 FULL、三个随机名单、三个空间名单；完整条件 64 个候选，其余各 48 保留/16 删除，互斥且完整。
- 来源在准备前后重新验核；旧源未修改，没有运行旧算法、影像处理或新编码。

## D 尚需独立完成

独立核来源、参照与 ID/row，抽样复算描述子距离/参考误差；检查后续 B/C 输出、计数、NA、子集与存活集合。A 的 `input_audit.json` 是可质疑和复算的生产者证据，不是 D 的签字。B/C/D 的核心模块仍未实现。

## 来源与许可

原始数据来自 ReMIND Version 1，[TCIA 数据页](https://www.cancerimagingarchive.net/collection/remind/) 标注 CC BY 4.0；引用 Juvekar, P., Dorent, R., Kogl, F., et al. (2023)，[DOI](https://doi.org/10.7937/3RAG-D070)。许可要求和署名见 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。

实际使用的是 [CrossKEY 作者提供的 Case059 处理后 MRI 与合成 US](https://github.com/morozovdd/CrossKEY)，固定来源提交 `4be57958eefcb255ec49aa16de9c4bceef381cfe`。作者仓库的软件许可为 MIT；软件许可不自动证明每一份派生影像的独立再许可。此链尚未追溯匹配到原始 DICOM，不能声称完成该项验证。

本轮延续范围受控的团队研究交付，保留来源与处理说明，不将数组作为本仓 MIT 材料上传。公开再分发仍未授权；若需改变渠道或公开数据，先解决相应权限，不把“能够下载”当成授权证明。
