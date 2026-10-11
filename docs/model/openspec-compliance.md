# 模型线 OpenSpec 合规

> 适用：蒋励及所有改 `data_model/` 的人 ｜ 关联：`docs/common/openspec-rules.md`

## 🔴 铁律

**改特征口径 / 切分 / 标签方法 = 提 change；可复现优先于单元测试。**

## 1. 相关 change（当前）

| change | 覆盖步 | 状态 |
|---|---|---|
| `data-collection-and-szz-labeling` | ①–⑤ 数据/特征 | 已归档（留 5.4 未勾，Sprint 1 清零） |
| `model-training-and-delivery` | ⑥⑦ 训练/全量预测 | 已实现 |
| `model-expansion` | ⑧⑨ 覆盖矩阵/校准 | 剩 tasks 4.4 未勾，Sprint 1 清零 |

## 2. 口径升级规则

- 特征取值口径改动 → 升 `feature_version` 到 `v2` 并**全量重算**，不覆盖 v1（否则已产特征不可比）。
- 改了判据/口径/依赖版本 → **所有下游对照产物重跑**（子集运行覆盖报告、D4 改后须重跑窗口对照）。

## 3. 验收证据要求

- 别人照复现命令跑出同一份统计（±0）。
- 两类指标（Effort-unaware + Effort-aware）齐全。
- 覆盖矩阵与训练报告逐项差异为 0。
