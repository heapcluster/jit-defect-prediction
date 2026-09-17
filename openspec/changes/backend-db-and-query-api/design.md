# 设计：库表、查询接口与在线预测

> 只记录技术决策与取舍。范围与「不做什么」见 proposal.md，任务分解见 tasks.md。

## D1 建库方式：自研 init 脚本，不引入 Alembic

手册 §7 允许 Alembic 或建表脚本二选一。选 `python -m app.db init`（SQLAlchemy `metadata.create_all` + 建后索引断言）：

- 契约一 9/18 已冻结，schema 演变概率低，迁移历史管理的收益小；
- 少一类依赖，「一条命令建好库」自明；
- 若冻结后契约真的改字段，届时另开 change 引入 Alembic，不预付复杂度。

## D2 鉴权：固定令牌，请求头 `X-API-Key`

契约三 v1.2「鉴权细则」已冻结：固定 API Key、不做 JWT、令牌读 `.env` 的 `API_TOKEN`、失败 message 固定 `missing or invalid token`。实现照做，不再另行选型；本条仅记录与提案初稿（曾建议 Bearer）的差异以冻结文本为准。

## D3 「提交存在但无预测记录」的详情响应形态

契约三 v1.2 未写。选 `code=0`、`risk_score` 与 `model_name` 为 null、`explanation` 空数组：

- 40400 的语义是「目标不存在」，而提交本身存在，用 40400 会让前端「该提交不存在」的文案说谎；
- 与 `docs/pages.md` §5「空数据不是错误」同口径，前端按 null 渲染「尚未预测」态；
- 回填路径：9/23 冻结宣布前在 PR #6 评审意见提出补记；冻结后走契约变更流程（tasks 1.3）。

## D4 灌入幂等键（按表）

| 表 | 幂等键 | 理由 |
|---|---|---|
| `commit` | `commit_hash` | 对接主键，契约一唯一索引 |
| `commit_label` | `(commit_hash, label_method)` | 标签可重算、两套方法并存，同方法重跑覆盖 |
| `commit_feature` | `commit_hash` | 契约一 ER 为 1:1；口径升级靠 `feature_version` 列区分并整行更新 |
| `prediction` | `(commit_hash, model_name)` | 契约三 predict 幂等性「库里只保留最新一行」；模型迭代换新名不覆盖 |

灌入一律 upsert；同一文件重跑不产生重复行。

## D5 种子数据

`backend/scripts/seed_dev_data.py` 生成小体量（数十行）、命名带 seed 的数据，仅供联调与测试；真实数据一律走灌入脚本。种子只进本地数据库、不入库，也不得混入任何统计口径或证据截图。

## D6 模型加载与注册表

- 启动时扫描 `MODEL_DIR`（`.env`，默认 `<repo>/data_model/models/`）下的 `*.pkl`，`model_name` = 文件名主干；注册表存 `{model_name: (path, mtime, model对象)}`。
- 「默认最新」= 注册表中 mtime 最大者；`predict` 与查询接口的 `model_name` 缺省同此口径。
- 加载失败（文件缺失、反序列化异常）**不阻断启动**：查询接口仍可用（读库），`predict` 返回 `50000`；异常详情只写服务端日志，message 不回显路径（契约三第 4 节错误情形）。
- 特征向量顺序固定按契约二 §3 的 14 列顺序组装，不按 dict 插入顺序猜（`backend/README.md` 红线）。

## D7 predict 落库：按 (commit_hash, model_name) upsert

契约三要求「同一 `(commit_hash, model_name)` 重复调用，库里只保留最新一行」。选 update-or-insert，并给 `prediction` 加 `(commit_hash, model_name)` 唯一索引把口径落进 schema：

- 契约一「不写进契约的」明确允许后端自属的冗余索引设计，加索引不构成契约偏离；
- 方案 C 的离线灌入与方案 A 的实时推理写同一张表、同一名键，天然互不累积重复行；
- 「模型迭代换新名、不覆盖旧结果」不受影响 —— 换名即新行。

## D8 SHAP 解释的 Explainer 选择

契约三冻结结论定为 SHAP、树模型用 TreeExplainer。实现按模型类型分派：

- 树族（DecisionTree / RandomForest / GradientBoosting / XGB*）→ `TreeExplainer`；
- 线性族（LogisticRegression 等）→ `LinearExplainer`；
- 其他不可支持的类型 → `explanation` 返回空数组并写服务端日志（前端按 pages.md「该模型未提供特征解释」渲染），风险值照常返回。

`contribution` = |shap 值|，`direction` = shap 值符号（正 `increase`、负 `decrease`）；排序与截断由前端负责（pages.md §3），接口返回全量。

## D9 测试双：SQLite 内存库 + fixture 模型

真 MySQL 凭据与数据线 `.pkl` 交付均不在手：单元测试用 SQLite 内存库（SQLAlchemy 可移植方言）与测试内 pickle 的小决策树 fixture；MySQL 8 真库自检与真模型压测留到任务 5.3 与周报任务 10，凭据/交付到位后补证据并登记。
