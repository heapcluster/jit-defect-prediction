# 模型预测（功能 5）

实现状态：已实现　期次：一期

## 一句话概述

独立的预测工具：加载指定 `model_package.zip`，对单提交、上传文件或可选数据集执行风险预测，交付统一 `predictions.csv`，并提供 load/unload/reload/default 四项模型管理操作。

## 1 职责与不负责范围

**负责**：

- 校验并加载模型包，构造与模型线匹配的特征，输出风险概率、二分类标签、风险等级和完整版本信息。
- 单条同步预测，以及批量/文件/可选数据集的异步预测；批量任务提供进度、成功失败计数、重试和下载。
- 提供模型加载、卸载、重载、设默认四个独立操作，查询可用、加载中、加载失败、已卸载等状态。
- 管理默认模型、批量大小、缓存与重试配置；支持预测幂等、过期标记和显式重新计算。

**不负责**：

- 训练或调参、性能评估、XAI 解释、行级定位、修复建议和数据采集。
- 在 predict 服务内调用解释或定位；提交详情只作为外部编排方并行调用各独立工具。
- 用前端常量或模型版本号单独决定默认模型，或把预测概率改写成经过阈值处理的数值。

## 2 独立运行入口

```bash
python -m app.cli predict run \
  --model-package model_package.zip --input cleaned.csv \
  --threshold 0.5 --out ./out
python -m app.cli predict one --commit <hash> --model rf_v1
python -m app.cli models load --package model_package.zip
python -m app.cli models set-default rf_v1
```

| 入口 | 命令 / 端点 | 契约 |
|---|---|---|
| CLI | `predict run/one`、`models load/unload/reload/set-default/status` | 文件与模型包即可批量运行；单条和模型管理共用同一实现 |
| 批量 API | `POST /api/predict/run` | multipart 上传模型包与输入文件，或指定已登记模型；返回 `kind=predict_batch` 的 `job_id` |
| 单条 API | `POST /api/predict` | 接收 `commit_hash` 与可选 `model_name`，同步返回，供详情编排保留 |
| 模型管理 | `GET /api/models/status`；`POST /api/models/{name}/load\|unload\|reload`；`PUT /api/models/default` | 四项管理动作显式触发，与页面刷新无关 |
| 任务管理 | `GET /api/jobs/{id}`、`POST /api/jobs/{id}/retry\|cancel` | 批量进度、日志、重试和取消 |
| 下载 | `GET /api/predict/outputs/{job_id}/{name}` | 下载 predictions、统计与 manifest |

所有 HTTP 端点（含模型管理与输出下载）必须使用 `X-API-Key`。run 的可选 `dataset_id` 只选择已导入的输入文件；上传模型包和数据文件时不依赖该选项。

## 3 输入契约

- 模型输入遵循 [`../file-contracts.md`](../file-contracts.md) §3.3 `model_package.zip`，加载前校验 `checksum.sha256`、`model_meta.json`、`feature_order.txt` 和特征列宽。权重损坏、版本不兼容或列宽不符必须拒绝，不猜测特征。
- 批量主输入遵循 §3.2 `cleaned.csv`；专家线也可接收 §3.1 `commits.csv`。语义/融合/端到端线所需的文本或向量必须与包内特征版本一致，缺输入时明确报错，不编造向量。
- run 配置包含模型标识或模型包、`decision_threshold`、筛选条件、`batch_size`、`force_recompute` 和输出格式；可选 `dataset_id` 仅作便利输入。
- 单条 `POST /api/predict` 的 `commit_hash` 为 40 位 hex；多余字段拒绝。详情可选择“沿用库中结果”或“立即重新计算”，后者显式设置重算语义，不影响批量文件工具。
- 默认模型解析顺序：`user_config.default_model`；未配置或不可用时回退到已加载 expert 模型中 `version_key` 最大者。回退原因必须可见。

## 4 输出契约

| 输出 | 文件 / 响应 |
|---|---|
| 批量预测 | `predict_predictions_<job_id>.csv`，可选 `.xlsx`；schema 严格遵循 §3.4，概率保留 5 位小数，标签按本次阈值生成 |
| 批量统计 | `predict_summary_<job_id>.json`：输入数、成功/失败数、实际模型与版本、阈值、缓存命中、重试和过期结果统计 |
| 单条响应 | 返回提交、实际模型、风险概率、预测标签、风险等级、决策阈值、模型/特征版本、预测时间与 stale 标记 |
| 模型状态 | 返回工件可用状态、运行时加载状态、默认模型、回退原因与最近加载错误 |
| manifest | 每个批量产物伴同名 `predict_<artifact>_<job_id>.manifest.json`，满足 §3.9，记录模型包与输入 checksum、配置和代码版本 |

所有文件遵循 `<module>_<artifact>_<job_id>.<ext>`。`risk_score` 始终保持模型概率；`decision_threshold` 只影响标签，`risk_high_threshold/risk_mid_threshold` 只影响展示等级。predict 响应与文件均不含 explanation，也不因解释或定位不可用而失败。

## 5 可配置项

| 配置 | 来源 | 默认 / 约束 |
|---|---|---|
| `default_model` | `user_config` 全局键 | 配置优先；空值按既定 expert 回退规则 |
| `decision_threshold` | `user_config` 全局键或 run 覆盖 | 默认 0.5，开区间 (0,1) |
| `risk_high_threshold` / `risk_mid_threshold` | `user_config` 全局键 | 默认 0.5 / 0.2，mid < high |
| `predict.batch_size` | `user_config` 命名空间键 | 正整数，控制批量分片，重启恢复 |
| `predict.cache_ttl` | `user_config` 命名空间键 | 非负时长；模型/特征版本变化使缓存失效 |
| `predict.retry_max` | `user_config` 命名空间键 | 非负整数，限制任务重试 |
| 自动加载策略 | train 的 `auto_load` + 本模块显式管理 | 默认手动或一键加载；不依赖页面刷新 |
| `default_dataset` | `user_config` 全局键 | 仅作 run 下拉默认选项 |

## 6 状态持久化

- 批量预测写 `job.kind=predict_batch`，使用统一五态并持久化入参、进度、错误日志和输出引用；同 kind 互斥，重启遗留 running 置 failed。
- 输出落盘 `backend/var/outputs/<job_id>/`，目录整体加入 gitignore；任务重试沿用配置快照和已持久化进度，不重复已完成的幂等结果。
- 可选导入 storage 后，`prediction` 按 `(commit_hash, model_name)` 幂等 upsert；模型或特征版本变化可将旧结果标记 stale，文件本身仍保留原版本事实。
- 模型加载失败保留原因并回退上一个可用模型；新模型通过显式操作或 train 完成通知加载，无需重启。模型重载与数据采集是不同操作。
- `predict.*` 与默认模型配置落 `user_config`，重启恢复；每次运行记录模型包 checksum、版本、阈值和缓存配置，确保结果可追溯。

## 7 与其他模块边界

- 与 train 仅通过 §3.3 模型包兼容；与 clean/collect 仅通过 §3.1/§3.2 数据文件兼容。上游服务不在场也可完成批量预测。
- evaluate 可接收 §3.4 文件；explain/localization 可按各自契约使用预测文件，但 predict 不反向调用它们。
- 提交详情需要解释时，由详情编排并行调用 predict 与 explain；解释失败不改写预测响应。

> W8 已移除 prediction 响应的 explanation 与预测服务内部 SHAP 调用，详情通过 `/api/explain` 独立编排；features/summary 继续供详情展示。prediction 已落 `model_version / feature_version` 可空列，单条沿用库中结果按行内版本与当前模型/特征版本对比返回真实 stale（历史 NULL 版本视为过期），force_recompute 重算刷新。批量已支持 semantic/fused/e2e 线（特征表 + 预计算/在线编码向量，e2e 文本表，e2e 不接受上传包）。CLI 为 `python -m app.cli predict run/one`、`models load/unload/reload/set-default/status`。
- storage 只负责可选展示导入和配置/任务持久化；不导入库也能下载、复验和交付全部预测文件。

## 8 验收标准

fixtures 位于 `tests/fixtures/files/predict/`，含正常、边界、非法三类模型包和输入文件；在无训练服务、无解释服务且库空的情况下，CLI/API 均可独立产出 §3.4 文件。

- 单条同步返回概率、标签、阈值与版本；批量可选择模型和输入文件，结果可下载并可选导入查询，重复执行无重复库记录。
- load/unload/reload/default 四操作分别生效；默认配置重启后保持，未配置时回退到已加载 expert 的最大 `version_key`。
- checksum 错误、权重缺失、特征列不符、空输入均有明确错误；加载失败回退不中断已有可用模型，模型重载不触发数据采集。
- 新训练模型可自动或一键加载，无需重启；模型/特征版本变化能标记 stale，“沿用库中结果”和“立即重新计算”语义清晰。
- 响应与输出不含 explanation；自动化依赖断言证明 predict 服务没有调用 explain/localization，解释失败不影响预测。
- 承接 TODO/05：单条、批量、数据集预测、模型管理、自动加载、幂等、过期重算与结果导出均有测试；`predict.*` 配置、五态、互斥和重启恢复通过。
