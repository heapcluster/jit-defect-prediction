# 技术架构与三端分包

> 合并自原 `docs/sprint0-scope.md` 第 1–4 节 + 原 `docs/dev-handbook.md`（已并入 `common/dev-handbook.md`） ｜ 审核：蒋励
> 课程要求「技术架构应服务于实际产品，建议三层架构/微服务架构」。本系统采用**单体三层 + 插件化模型注册表**，
> 不拆微服务：数据规模与团队规模都不需要分布式，拆开只会增加联调成本。

## 1. 系统定位（三个限定词，写在最前面避免过设计）

- **提交粒度**：预测单位是 commit，不是文件/行/需求。
- **建议性预警**：只做风险排序供评审参考，**不做 CI 强制拦截**。
- **单仓库**：数据源固定 Apache Camel（`camel-4.23.0`），不做跨项目迁移
  （Kamei et al. 2013 结论：JIT 模型跨项目不可迁移）。

## 2. 分层架构

```
┌──────────────────────────────────────────────────────────┐
│ 表现层  frontend/          Vue 3 + Element Plus + ECharts │ 3 个页面
├──────────────────────────────────────────────────────────┤
│ 接口层  backend/app/api/   FastAPI：鉴权 + 校验 + 错误码包络 │ 5 个接口
│ 领域层  backend/app/       model_registry / feature_source │ 模型与特征装配
│ 持久层  backend/app/       SQLAlchemy ORM（4 张表）        │
├──────────────────────────────────────────────────────────┤
│ 数据/模型层 data_model/    离线：抽取→打标→特征→训练→全量预测 │ 不直连数据库
└──────────────────────────────────────────────────────────┘
```

分层纪律：**上层可依赖下层，反向依赖即缺陷**。接口层不写 SQL，表现层不拼 SQL，
数据线不 import `backend`。

## 3. 三端分包方案

| 包 | 职责 | 技术栈 |  owner | 对外产物 |
|---|---|---|---|---|
| `frontend/` | 三页面渲染、筛选与图表、错误码三态 | Vue 3 / Vite / Element Plus / ECharts | 刘帅华 | 静态站点（`dist/`） |
| `backend/` | HTTP 接口、鉴权、ORM、模型加载与推理、SHAP 解释 | Python 3.12 / FastAPI / SQLAlchemy / Uvicorn | 吕建江 | 可运行服务 |
| `data_model/` | 数据采集、SZZ 打标、特征提取、训练评估、模型与预测文件 | Python 3.12 / scikit-learn / XGBoost / LightGBM / PyTorch | 蒋励 | `.pkl` 权重 + `prediction_result.csv` |
| `infra/` | 分支与 PR 规范、CI、缺陷治理、规格校验脚本 | Python / GitHub Actions | 苏哲勋 | CI 与规范基线 |
| `docs/` `openspec/` | 契约、设计、验收、规格与变更提案 | Markdown | 全员（蒋励统稿） | 契约与规格 |

### 3.1 各包内部分层（统一到业界常见切法）

```
frontend/src
  api/        接口封装（只认契约三字段，不自行发明字段）
  views/      页面（风险列表 / 提交详情 / 趋势看板）
  components/ 可复用组件
  utils/      纯函数（如 models.js 模型清单，与交付清单同源）

backend/app
  api/        路由层：参数校验、错误码映射，不含业务规则
  models.py   ORM 实体（4 张表）
  schemas.py  响应结构（统一 { code, message, data } 包络）
  model_registry.py  模型插件注册表（加载 .pkl + 可插拔解释）
  feature_source.py  单条提交特征现算（复用数据线 v1 口径）
  db.py / config.py / auth.py / errors.py  基础设施

data_model/pipelines
  expert/ semantic/ fused/ e2e/   四条分类器线，各自 config + train
  preparation/（01–05）             数据准备与切分（四线共享产物）
  common 口径由 config-and-output-spec / 契约二约束
```

### 3.2 依赖方向（铁律）

```
frontend ──HTTP──▶ backend ──读 .pkl / 调 .py──▶ data_model 产物
   │                   │                            │
   └──── 契约三 ───────┴──── 契约一/契约二 ─────────┘
```

- 前端**只通过 HTTP 依赖后端**，不得直接读库或读模型文件。
- 后端**只通过文件依赖数据线**（`MODEL_DIR` 下的 `.pkl` + `feature_order.txt`），
  不得 import `data_model` 的训练代码。
- 数据线**不直连数据库**，产物只落文件，灌库责任在后端（C 方案裁定）。

## 4. 跨端契约（改契约 = 走 change，不得口头约定）

| 契约 | 文件 | 约束什么 |
|---|---|---|
| 契约一 | `docs/design/data-fields.md` | 库表字段与 ER（4 张表） |
| 契约二 | `docs/model/feature-columns.md` | 14 项特征列名与顺序（唯一权威） |
| 契约三 | `docs/backend/api-spec.md` | 接口请求/响应/错误码/非功能 |
| 交付清单 | `data_model/pipelines/expert/models/feature_order.txt` | 在线可加载模型（契约二的副本，不是权威） |

## 5. 运行时视图（三条主链路）

**① 在线查询（读）**
前端 → `GET /api/commits` / `/api/commits/{hash}` / `/api/trends` → ORM → MySQL → 统一包络返回。

**② 在线预测（写 + 算）**
`POST /api/predict`（单条）或 `POST /api/sync`（批量拉取最新提交）→
特征现算（14 项，复用数据线 v1 口径）→ `model_registry` 选模型推理 →
SHAP 解释 → 落 `commit` / `commit_feature` / `prediction` 三张表 → 返回。
- 8 个模型全部在线可切换（`lr_v1` … `tabnet_v1`，Issue #139 组长裁定）；
- 树族与线性模型（lr/rf/xgb/lgbm/et）归因非空，核/深度模型（svm/mlp_deep/tabnet）
  无高效精确解释器，按设计降级为 `explanation: []`，前端渲染「该模型未提供特征解释」。

**③ 离线训练与交付（写文件，不碰库）**
Camel 仓库 → 抽取提交 → SZZ 打标 → 14 项特征 → 时间序切分 → 训练 8 个分类器 →
导出 `.pkl` + `feature_order.txt`（+ 全量 `prediction_result.csv`，仅作评估对照）→ 后端按 `[models]` 段加载。
**入库只走实时同步端点**（`POST /api/sync` / `POST /api/sync-prs`），离线 CSV 灌库已于 2026-10-25 移除。

## 6. 关键组件：`model_registry`（插件化）

- 启动时按 `feature_order.txt` 的 `[models]` 段加载；清单缺失或列序与契约二不符 → 注册表为空，
  查询服务仍可用，预测返回 50000（错误详情只进服务端日志，不回显路径）。
- 单个权重加载失败只跳过该模型，不拖垮启动。
- 新增/移除在线模型须另开 change 走契约变更，**不得静默切换**。

## 7. 外部依赖

- Apache Camel 仓库（固定 `camel-4.23.0`）—— 数据来源，不入库。
- GitHub（协作 / PR / Issue / OpenSpec）、飞书多维表格（看板 / 周报）。
- 运行环境与依赖版本以 `data_model/environment.yml` 为唯一清单（不再维护第二份）。

## 8. 架构决策摘要

| 决策 | 选择 | 理由 |
|---|---|---|
| 架构形态 | 单体三层，不拆微服务 | 数据规模与团队规模均不需要分布式 |
| 模型接入 | 文件交付 + 注册表插件化 | 训练与在线解耦，训练口径变化不影响接口 |
| 模型数量 | 训练 8 个、在线 8 个 | 课程「至少 2 类不少于 8 种」，且已裁定全部上线 |
| 归因能力 | 与预测能力分离 | 不把秒级 KernelSHAP 放进 500ms 请求路径 |
| 数据库 | ORM + 单一 DATABASE_URL 配置 | 统一 MySQL，联调 / 演示 / 验收同一套 |
