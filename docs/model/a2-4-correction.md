# S6+1：A2-4 判据方向订正（仓库侧已对齐）

> 任务：苏哲勋 S6+1 ｜ 登记 Issue #59 ｜ 仓库侧权威：`docs/model/data-pipeline.md` 第 6 节
> 状态：仓库侧已对齐，飞书《产品需求文档》A2-4 待苏哲勋镜像订正。

## 1. 问题

飞书 PRD 的 A2-4 写：「正样本比例**落在 40%–60% 之外**时告警」。
但 `docs/model/data-pipeline.md` 第 6 节写：「落在 40%–60% **之间**就停下来先查打标逻辑」。

**两处方向相反**：一个说「之外告警」，一个说「之内查」。课程判定「规格与代码/文档不一致 = 缺陷」。

## 2. 裁定（以 data-pipeline.md 为准）

- **正确口径**：正样本比例落在 **40%–60% 之间** → 停下自查打标逻辑（判据实现 `02_szz_labeling.py` 的 `ABNORMAL_LOW,HIGH = 0.40,0.60`）。
- 当前 Camel 样本实测 `szz` **22.23%**、`szz_lite` **14.38%**，均在区间外，通过；旧版 **38.98% / 27.74%** 属 ActiveMQ 历史实验，不用于当前验收。数值见 `data_model/preparation/reports/dataset_stats.md`，判定方向见 `openspec/specs/szz-labeling/spec.md`。

## 3. 苏哲勋要做的（飞书侧）

- 将 PRD A2-4 改为「落在 40%–60% **之内**就先查打标逻辑」，与 `data-pipeline.md` 对齐。
- 核对 `data_model/preparation/reports/dataset_stats.md` 复述处：当前已写「落在 40%–60% 才需自查」，两组 Camel 比例也按区间外判通过；无须反向改写。
- Issue #59 收口。

## 4. 为什么不纠结

课程要求「需求变更必须同步修改管理工具及 OpenSpec change 记录」。本项仓库侧已对，飞书侧补一句即可，是改一句的小活，但 sober 在 #55 复审点名过，须收口。
