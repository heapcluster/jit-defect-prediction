# 撤销「本地开发数据初始化」，空库一律按需现算

## Why

owner 裁定：**不允许提前灌库**。2026-10-26 短暂存在的 `infra/bootstrap_dev.py`（从本机 CSV 直灌 3000 条 + 预跑预测）与项目卖点相悖 —— JIT 缺陷预测的核心叙事就是「数据从 git 历史现算进来」；且数据线产物（`data_model/data/*.csv`）与权重 `.pkl` 均被 `.gitignore` 忽略，该脚本对其他机器是死路。业界口径同时确认：预测颗粒度是 commit/变更级（Kamei et al., TSE 2013；SZZ 回溯），PR/MR 是审阅聚合单元 —— 项目现有 `/api/commits` + `/api/prs` 聚合结构不动，要改的只是「数据怎么进来」。

## What Changes

- `db-schema`：**修改**「实时同步入库」—— 撤销「本地开发初始化」例外段，恢复「MUST NOT 保留离线 CSV 灌库路径」的完整口径，并新增「空库首启」Scenario（查询端点空列表 code=0，不 50000；数据靠界面触发同步逐条进来）。
- `db-schema`：**移除**「本地开发数据初始化」Requirement。
- 代码：**删除** `infra/bootstrap_dev.py`。
- 前端：`RiskList` / `PrList` 空库与预测缺失时提供**同步加载台**（说明现算成本、分批触发同步、逐批反馈进度）。

## Capabilities

### Modified Capabilities

- `db-schema`: 数据入口口径收紧回「只有实时同步」，空库首启行为写进规格。

## Impact

- 规格：`openspec/specs/db-schema/spec.md`（归档后生效）。
- 代码：删除 `infra/bootstrap_dev.py`；前端 `RiskList.vue` / `PrList.vue` / `PrDetail.vue` 的同步引导与加载台。
- 文档：`README.md` §7.3、`docs/backend/mysql-setup.md` §4.4、`docs/common/local-runbook.md` 撤销 bootstrap 口径。

## 不做什么

- 不改契约一/二/三的字段、类型、接口格式与错误码；不改预测颗粒度（commit 为预测单元、PR 为聚合视图，即业界混合标准）。
- 不做后台自动同步（`SYNC_ON_STARTUP` 保持默认关）。
- 不删除 `infra/clone_camel_history.py` —— 建历史索引是同步的正规前置步骤。