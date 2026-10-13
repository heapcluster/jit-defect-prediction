# 后端实现设计（含四张图）

> 负责人：吕建江 ｜ 合并自原 `docs/implementation/backend-design.md`（已并入本文件） ｜ 审核：蒋励
> 四张图均按课程硬要求标注「生成方式：<工具名+模型>｜提示词」。图是设计稿，实现以 `api-spec.md` 与 `docs/design/database.md` 为准。
> **图源登记总表（全项目 14 张）见 `docs/design/diagrams.md` §1**；本节是后端线自用视图，与总表同源 —— 改一处须同步另一处（飞书《产品设计文档》5.1.2 为第三处）。

## 0. 技术选型

FastAPI + SQLAlchemy + MySQL（或 SQLite 开发期）；模型用 `joblib.load` 加载 `data_model/models/*.pkl`；解释用 SHAP（树模型 `TreeExplainer`）。

## 1. 系统架构图

```mermaid
flowchart TB
  subgraph 前端
    FE[Vue3+ElementPlus+ECharts]
  end
  subgraph 后端
    API[FastAPI 路由层<br/>commits/predict/trends]
    SVC[服务层<br/>风险查询/实时推理/解释]
    AUTH[鉴权中间件 X-API-Key]
    MR[model_registry<br/>加载.pkl+SHAP]
  end
  DB[(MySQL:<br/>commit/commit_label/<br/>commit_feature/prediction)]
  MODELS[data_model/models/*.pkl]

  FE -->|X-API-Key| AUTH --> API --> SVC
  SVC --> DB
  SVC --> MR --> MODELS
```

> 生成方式：CodeBuddy（AI 编程助手；Mermaid `flowchart` → 飞书画板渲染）｜提示词：「画 JIT 缺陷预测后端架构：前端经鉴权中间件调 FastAPI 路由，服务层读 MySQL 四表并调 model_registry 加载 pkl+SHAP 解释」

## 2. 请求处理流（以 GET /api/commits 为例）

```mermaid
sequenceDiagram
  participant C as 前端
  participant M as 鉴权中间件
  participant R as 路由层
  participant S as 服务层
  participant D as DB
  C->>M: GET /api/commits + X-API-Key
  M->>M: 校验令牌
  alt 缺失/不匹配
    M-->>C: 401 code=40100
  else 通过
    M->>R: 放行
    R->>S: 解析分页/过滤参数
    S->>D: 查 prediction  JOIN commit
    D-->>S: items + total
    S-->>R: data{items,total}
    R-->>C: 200 {code:0,data}
  end
```

> 生成方式：CodeBuddy（AI 编程助手；Mermaid `sequenceDiagram` → 飞书画板渲染）｜提示词：「画带鉴权的查询接口请求处理时序，含令牌失败分支与正常分支」

## 3. POST /api/predict 实时推理时序

```mermaid
sequenceDiagram
  participant C as 前端/调用方
  participant R as predict 路由
  participant MR as model_registry
  participant M as 模型.pkl
  participant D as prediction 表
  C->>R: POST {commit_hash,model_name}
  R->>R: 参数校验(40位十六进制)
  R->>MR: load(model_name)
  MR->>M: joblib.load
  R->>D: 取 commit_feature(14项,口径处理)
  R->>M: 推理 → risk_score
  R->>MR: shap.TreeExplainer → explanation[]
  R->>D: upsert (commit_hash,model_name) 幂等
  R-->>C: 200 {risk_score,features,explanation}
```

> 生成方式：CodeBuddy（AI 编程助手；Mermaid `sequenceDiagram` → 飞书画板渲染）｜提示词：「画在线预测实时推理时序：校验→加载模型→取特征→推理→SHAP解释→幂等upsert→返回」

## 4. 类图（核心模块）

```mermaid
classDiagram
  class AuthMiddleware {
    +verify(token:str):bool
  }
  class CommitRouter {
    +list_commits()
    +get_commit(hash)
  }
  class PredictRouter {
    +predict(body)
  }
  class TrendRouter {
    +trends(params)
  }
  class ModelRegistry {
    +load(name):Model
    +explain(features):list
  }
  class PredictionRepository {
    +upsert(hash,name,score)
    +query(filters)
  }
  CommitRouter --> PredictionRepository
  PredictRouter --> ModelRegistry
  PredictRouter --> PredictionRepository
  AuthMiddleware <|-- CommitRouter
```

> 生成方式：CodeBuddy（AI 编程助手；Mermaid `classDiagram` → 飞书画板渲染）｜提示词：「画后端核心类图：鉴权中间件、三个路由、模型注册表、预测仓储，标依赖」

## 5. 分步实现清单（吕建江 L3/L4）

| 步 | 动作 | 验收 | OpenSpec |
|---|---|---|---|
| 1 | 按 `docs/design/database.md` 建四张表（Alembic 或 SQL 脚本） | 一条命令建库；字段逐字一致 | 已冻结，落库即实现 |
| 2 | 写鉴权中间件 + 错误码包络 | 缺令牌→401，`50000` 不回显内部 | 契约三 §1 |
| 3 | 实现三个查询接口 | 字段名零自创；空数据返回 `null` 非 404 | 契约三 §3 |
| 4 | 实现 `POST /api/predict` + 模型加载 + SHAP | 实时推理；幂等 upsert | change `predict-api` |
| 5 | 写性能压测脚本（`backend/scripts/`） | 95%<500ms 分位数截图 | change `nfr-evidence-scripts` |
| 6 | 写安全用例脚本 | 缺令牌/畸形参数两组截图 | 同上 |
| 7 | 设计文档订正（§四 1.3→1.4、补 #44/#47、合并重复节） | sober 验收可点开 | L3 设计文档 |

> 每一步都要走 PR（非作者审阅），勾 `tasks.md` + 附证据，才算完成（DoD 见 `docs/design/README.md`）。
