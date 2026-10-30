# 附加功能立项（缺陷可视化定位 + 高质量修复建议 + 公开数据集）

> Sprint 3 候选 ｜ 起草 2026-10-09 ｜ 起草人 蒋励 ｜ 关联契约：docs/{backend/api-spec.md, design/data-fields.md, model/feature-columns.md}（契约三，冻结日期见各文件头）
>
> ⚠️ 契约基线判定沿用首 change：以各契约文件头的「版本 + 冻结日期」为准，不引用 PR 编号或合并时机。

## Why
课程《项目要求》鼓励在 MVP 之外做附加功能。0925 周报已写「排 Sprint 3」，但看板与 openspec
至今没有对应条目——写了就得有东西可点，否则会烂尾。四项候选：
1. 缺陷可视化定位：在提交详情页把 SHAP 归因落到具体文件 / 代码行，而非仅给特征权重。
2. 高质量修复建议：基于历史修复提交，对高风险提交给出「参考修复模式」建议。
3. 公开数据集加载与质量治理：~~加载公开 JIT 数据集并治理其固有问题（标签粒度、语种、数据质量）~~ —— 课程 2026/10/12 新增，**已于 2026-10-13 移出本 change**：课程附加功能 (3) 指出现有 JIT 数据集三大缺陷（标签粒度过粗、主要针对 Java、数据质量），而本组单仓库 + SZZ 代理打标的现状恰好完整复刻这三条。已另立 change **`public-dataset-quality`**（Sprint 2 启动，逐条回应三个问题，含「可下载性验证不过则降级并如实说明」的阻塞前置）。
4. ~~预训练语义特征建模~~ —— 课程 2026/10/12 新增，**已于 2026-10-13 移出本 change**：经任课教师指导与课程附加功能 (4)（「早期方法基于专家特征，现在主流方法是预训练模型提取深层语义特征」）判定，语义特征不应作为可选附加，而应提升为模型线主线。已另立 change **`semantic-feature-mainline`**（Sprint 2 启动，Kamei 14 降为基线对照组），规格见该 change 的 `specs/semantic-features/spec.md`（7 条 Requirement，覆盖原 G1-4 全部内容并扩充）。
两项均不在 Sprint 1 交付范围，须先立项以便看板可追踪。

## What Changes
1. 新增看板 Sprint 3 行（或本 change 的 tasks 即对应条目），使 J7 验收「列点得开」。
2. 缺陷可视化定位：前端详情页接入文件级 SHAP / 行级高亮。
3. 高质量修复建议：检索历史修复提交，输出 Top-K 参考。
4. 公开数据集：加载器对齐现有 schema + 质量问题治理与质量报告。
5. ~~语义特征：预训练模型提取语义特征 + 专家 / 语义 / 融合三类对比实验。~~ **已移出**，见 change `semantic-feature-mainline`。

## Capabilities
- `defect-visualization`：提交详情页的文件 / 行级缺陷定位可视化。
- `fix-suggestion`：基于历史修复的高风险提交修复建议。
- `public-dataset`：公开 JIT 数据集加载、质量治理与基线对照。
- ~~`semantic-feature`~~：**已移出**至 change `semantic-feature-mainline`（capability 改名 `semantic-features`，规格更完整）。

## Impact（影响与边界）
| 项 | 内容 |
|---|---|
| 影响目录 | frontend/（详情页）、data_model/（可选检索脚本、数据集加载器、语义特征提取） |
| 不做什么 | 不改交付模型与契约字段名 / 列名 / 接口路径；公开数据集与语义特征均为**并列增强**，不替换 Kamei 14 基线与交付模型；Sprint 3 才实做，本期只立项 |
| 数据边界 | 检索中间产物不入库；只入库必要的小体积说明 |
| 新增依赖 | 预训练代码模型（CodeBERT / GraphCodeBERT 等）与公开 JIT 数据集，均不进入 MVP 交付链 |
