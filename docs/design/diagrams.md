# 核心设计图（四张图，含生成方式标注）

> 课程硬要求：架构图 / 流程图 / 时序图 / 类图，且 AI 生成的图必须标注来源。
> 每图下方记一行「生成方式｜提示词」。后端视图见 `docs/backend/implementation.md`。

## 图 1：系统架构图

```mermaid
flowchart TB
  subgraph 前端
    FE[Vue3+ElementPlus+ECharts]
  end
  subgraph 后端
    API[FastAPI 路由层]
    SVC[服务层]
    AUTH[鉴权中间件 X-API-Key]
    MR[model_registry 加载.pkl+SHAP]
  end
  DB[(MySQL 四表)]
  MODELS[data_model/models/*.pkl]
  FE -->|X-API-Key| AUTH --> API --> SVC
  SVC --> DB
  SVC --> MR --> MODELS
```

> 生成方式：Mermaid `flowchart` ｜ 提示词：「JIT 缺陷预测后端架构：前端经鉴权中间件调 FastAPI，服务层读 MySQL 四表并调 model_registry 加载 pkl+SHAP」

## 图 2：请求处理流（以 GET /api/commits）

```mermaid
sequenceDiagram
  participant C as 前端
  participant M as 鉴权中间件
  participant R as 路由层
  participant S as 服务层
  participant D as DB
  C->>M: GET /api/commits + X-API-Key
  M->>M: 校验令牌
  alt 失败
    M-->>C: 401 code=40100
  else 通过
    M->>R: 放行
    R->>S: 解析分页/过滤
    S->>D: 查 prediction JOIN commit
    D-->>S: items+total
    S-->>R: data
    R-->>C: 200 {code:0,data}
  end
```

> 生成方式：Mermaid `sequenceDiagram` ｜ 提示词：「带鉴权的查询接口请求处理时序，含令牌失败与正常分支」

## 图 3：POST /api/predict 实时推理时序

```mermaid
sequenceDiagram
  participant C as 调用方
  participant R as predict 路由
  participant MR as model_registry
  participant M as 模型.pkl
  participant D as prediction 表
  C->>R: POST {commit_hash,model_name}
  R->>R: 参数校验(40位十六进制)
  R->>MR: load(model_name)
  MR->>M: joblib.load
  R->>D: 取 commit_feature(14项)
  R->>M: 推理 → risk_score
  R->>MR: shap → explanation[]
  R->>D: upsert 幂等
  R-->>C: 200 {risk_score,features,explanation}
```

> 生成方式：Mermaid `sequenceDiagram` ｜ 提示词：「在线预测实时推理时序：校验→加载模型→取特征→推理→SHAP→幂等upsert→返回」

## 图 4：类图（核心模块）

```mermaid
classDiagram
  class AuthMiddleware { +verify(token):bool }
  class CommitRouter { +list_commits() +get_commit(hash) }
  class PredictRouter { +predict(body) }
  class TrendRouter { +trends(params) }
  class ModelRegistry { +load(name):Model +explain(features):list }
  class PredictionRepository { +upsert(hash,name,score) +query(filters) }
  CommitRouter --> PredictionRepository
  PredictRouter --> ModelRegistry
  PredictRouter --> PredictionRepository
  AuthMiddleware <|-- CommitRouter
```

> 生成方式：Mermaid `classDiagram` ｜ 提示词：「后端核心类图：鉴权中间件、三个路由、模型注册表、预测仓储，标依赖」
