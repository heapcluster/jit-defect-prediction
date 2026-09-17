# 库表、查询接口与在线预测

> Sprint 0–1 ｜ 对应飞书周报任务 7（库表与接口格式，负责人吕建江）与任务 8 的后端相关动作；做法与验收见 `docs/dev-handbook.md` §7、§8
> 起草 2026-09-17 ｜ 起草人 吕建江 ｜ 对齐契约：`data-fields.md` v1.2（冻结 9/18）、`api-format.md` v1.2（冻结 9/23）、`feature-columns.md` v1.0（冻结 9/18）—— 三份冻结文本在 PR #6（`docs/docs/freeze-contracts-v1`）

## Why

- 后端目录目前只有 README 与依赖清单，**没有任何可执行代码**。上游数据链路已跑通（01–04 脚本与统计已产出），前端三个页面的字段映射已在 `docs/pages.md` 成文 —— 两端都在等「表建好、接口通」。
- 课程《项目要求》把「**预测与解释模块**」列为必做模块、要求「**对外提供在线预测服务**」；契约三 v1.1 据此补了 `POST /api/predict`（1.0 版曾误封「只有三个接口」，补记见契约冻结结论）。只读查询不构成预测服务，本 change 必须把实时推理做出来。
- 接口契约 9/23 冻结。**冻结应当被实现反向验证**：四个接口若不先落成代码、用 FastAPI 自动生成的 Swagger 逐字段比对，偏离会在联调时才暴露，返工成本全落在前端线。
- 库表是裁定 A+C 的落点：方案 C 的 `prediction_result.csv` 与 01–03 的提交/标签/特征 CSV 都等后端建表灌入；方案 A 的 `.pkl` 等后端加载器。
- 鉴权方式、灌入幂等键、predict 落库口径都是**不可逆的口径决定**，已在契约冻结时定死（见文末裁定记录），实现只许照做、不许即兴。

## What Changes

- **新增 `db-schema` 能力**：按契约一 v1.2 建**四张表** `commit` / `commit_label` / `commit_feature` / `prediction`（建表归属见契约一「建表归属」节），字段名、类型、索引（`commit_hash` 唯一索引、`committed_at` 普通索引）逐字照契约；`commit_feature` 列名照契约二；满足「别人 clone 后一条命令建好库」；四份 CSV 的灌入脚本；`.env.example` 入库、`.env` 不入库。
- **新增 `query-api` 能力**：按契约三落地三个查询接口 `GET /api/commits`、`GET /api/commits/{commit_hash}`、`GET /api/trends`；统一响应包络、只用 5 个错误码、`X-API-Key` 鉴权（40100）、输入校验（40001）、`50000` 不回显内部信息。
- **新增 `predict-api` 能力**：`POST /api/predict` 在线预测 —— 启动时加载 `data_model/models/` 下的 `.pkl`（方案 A），实时推理 + SHAP 解释；结果按 `(commit_hash, model_name)` 幂等落 `prediction` 表、只留最新一行（方案 A 与 C 同表、靠 `model_name` 区分）；模型缺失/加载失败返回 `50000` 且只写服务端日志。
- **Swagger 实现镜像**：以 FastAPI 自动生成的 OpenAPI 与契约三 v1.2 逐字段比对，偏离改代码不改契约。

**不做什么（显式列出）**

- **不做**性能与安全证据脚本 —— 周报任务 10 另开 change；本 change 只实现鉴权、校验与推理本身（压测靶子已明确为 `POST /api/predict`）
- **不做**方案 B（后端起子进程调推理脚本）—— 已过裁定否决：解释器启动耗时就过不了 95% < 500ms
- **不做**前端页面与图表；**不新增** `GET /api/models`（模型清单 MVP 由前端维护，见契约三冻结结论）
- **不改**契约字段名与列名 —— 缺口一律走契约变更流程
- **不做**同图多模型对比、趋势按作者/子系统分组（契约三冻结结论已否）

**是否触及 `docs/sprint0-scope.md` 的边界**：**不触及**。落在该文第 2 节「做」的「接口的输入校验与鉴权」与完整链路之内；模型加载属第 4 节已裁定的跨线接口 A+C，不改变系统定位与四条线目录边界。

## Capabilities

### New Capabilities

- `db-schema`: 四张表建表与索引、一条命令建库、四份 CSV 灌入（提交/标签/特征/预测）
- `query-api`: 三个查询接口、统一包络与错误码、`X-API-Key` 鉴权与输入校验
- `predict-api`: 模型加载、`POST /api/predict` 实时推理、SHAP 解释、预测结果幂等落库

### Modified Capabilities

无 —— `openspec/specs/` 尚无归档产出，没有被修改的既有能力。

## Impact

| 项 | 内容 |
|---|---|
| 影响目录 | `backend/`（应用代码、测试、灌入与种子脚本）；`backend/requirements.txt`（新增 scikit-learn / xgboost / shap / numpy，依据裁定 A+C 与契约三冻结结论的 SHAP） |
| 消费的契约 | `data-fields.md` v1.2 四张表与 ER 图、`api-format.md` v1.2 四接口、`feature-columns.md` v1.0（`commit_feature` 列名与特征顺序）—— 只读不改 |
| 上游依赖 | 数据线 01–04 产出的四份 CSV；上游 change `model-training-and-delivery` 交付的 `.pkl`、`model_name` 与 shap 依赖信息（分支 `docs/spec/model-training-delivery`，未合入）；接口与推理自测先用种子数据与 fixture 模型，不等真实交付 |
| 下游依赖 | 前端三页面联调（刘帅华）；周报任务 10 的性能与安全证据脚本（压测靶子 `POST /api/predict`） |
| 数据边界 | `.env`、数据集、模型文件一律不入库；种子数据与 fixture 模型只进本地，不入库 |

## 裁定记录（原「待决问题」，2026-09-17 结清）

| 项 | 结论 | 出处 |
|---|---|---|
| `commit_feature` 是否建表 | **建**，四张表全由后端建、同一份迁移脚本 | 契约一 v1.2「建表归属」节（PR #6） |
| 鉴权方式 | **固定令牌，请求头 `X-API-Key`**，不做 JWT；细则与已接受代价见契约三 v1.2「鉴权细则」 | 契约三 v1.2（PR #6） |
| 模型交付 | **A+C**：A 启动加载 `.pkl` 供 predict 实时推理；C 离线结果灌 `prediction` 表；B 否决 | 飞书裁定 + 契约三 v1.1 补记、`backend/README.md` |
| 「提交存在但无预测记录」的详情响应形态 | 按 design D3：`code=0`、`risk_score`/`model_name` null、`explanation` 空数组。**契约三 v1.2 未收录此口径** —— 冻结宣布前在 PR #6 评审意见提出补记，或冻结后走契约变更流程 | 本 change design D3（待回填契约） |
