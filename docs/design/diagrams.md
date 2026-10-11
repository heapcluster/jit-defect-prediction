# 核心设计图（四张图唯一源码，含生成方式标注）

> 课程硬要求：架构图 / 流程图 / 时序图 / 类图，且 AI 生成的图必须标注来源。
> **本文件是飞书《产品设计文档》§四/§五 四张图与 `项目资料/diagrams/fig1-4.png` 的唯一源码**：改图先改本文件（走 PR），再重转飞书/重渲染 PNG，避免多处漂移。
> 每图下方独立一段「生成方式｜提示词」标注行；飞书里标注行须独立成段贴于图下，不得塞进代码块/白板内。
> 转换要求：飞书用 mermaid 代码块/白板渲染；PNG 导出用 mermaid-cli ≥3x 缩放白底（`项目资料/diagrams/` 为 10-11 渲染件）。

## 图 1：系统架构图（§四·系统架构）

```mermaid
flowchart TD
    subgraph 可视化层["可视化层（Vue 3 + Element Plus + ECharts）"]
        P1[风险列表页]
        P2[提交详情页]
        P3[缺陷引入趋势看板]
    end
    subgraph 接口层["后端 / API 层（Python 3.12 + FastAPI）"]
        A1[鉴权 X-API-Key]
        A2[输入校验 / 错误码包络]
        A3[查询接口 x3]
        A4[在线预测 POST /api/predict]
        A5[模型加载器 + SHAP 解释]
    end
    subgraph 数据与模型层["数据与模型层"]
        D1[(MySQL 8：commit / commit_label / commit_feature / prediction)]
        D2[模型文件 .pkl（数据线交付）]
        D3[CSV：01–03 提交/标签/特征 + 方案 C prediction_result.csv]
    end
    P1 & P2 & P3 -->|HTTP + X-API-Key| A1
    A1 --> A2 --> A3 & A4
    A4 --> A5 --> D2
    A3 --> D1
    A4 -->|幂等落库| D1
    D3 -->|python -m app.ingest| D1
```

> 生成方式：Qoder（LLM）｜提示词：「按 docs/contracts/ 三条契约与 backend/ 实现，画 JIT 缺陷预测系统三层架构图，标出组件、调用方向与外部依赖」

## 图 2：predict 核心流程图（§五·核心流程图，课程点名）

```mermaid
flowchart TD
    A[POST /api/predict 请求] --> B{X-API-Key 有效?}
    B -- 否 --> C[40100 missing or invalid token]
    B -- 是 --> D{commit_hash 为 40 位十六进制?}
    D -- 否 --> E[40001 参数非法]
    D -- 是 --> F{commit 表存在?}
    F -- 否 --> G[40400 commit not found]
    F -- 是 --> H{commit_feature 行存在?}
    H -- 否 --> I[40400 features not found for this commit]
    H -- 是 --> J{模型注册表有可用模型?}
    J -- 否 --> K[50000 internal error（只记日志）]
    J -- 是 --> L[按契约二 §3 顺序组 14 维向量]
    L --> M[predict_proba 实时推理]
    M --> N[SHAP 解释 Tree/Linear Explainer]
    N --> O[upsert prediction 按 commit_hash+model_name]
    O --> P[包络响应 risk_score/features/explanation]
```

> 生成方式：Qoder（LLM）｜提示词：「按契约三 v1.3 的错误路径与 change backend-db-and-query-api 的 predict 流程，画后端核心流程图 mermaid flowchart，含全部分支判定与错误码」

## 图 3：查询与预测时序图（§五·时序图，课程点名）

```mermaid
sequenceDiagram
    participant FE as 前端三页面
    participant API as FastAPI 接口层
    participant DB as MySQL 8
    participant MD as 模型注册表(.pkl)
    FE->>API: GET /api/commits（X-API-Key）
    API->>API: 鉴权 + 参数校验
    API->>DB: 联表 prediction+commit（单模型、risk 降序、分页）
    DB-->>API: 行集
    API-->>FE: 包络 {code:0, data{total, items[]}}
    FE->>API: POST /api/predict {commit_hash}
    API->>DB: 读 commit / commit_feature
    DB-->>API: 特征行
    API->>MD: 取模型（缺省=注册表版本序最大 version_key）
    MD-->>API: 模型对象
    API->>API: 实时推理 + SHAP 解释
    API->>DB: upsert prediction（幂等键）
    API-->>FE: 包络 {code:0, data{risk_score, features, explanation}}
```

> 生成方式：Qoder（LLM）｜提示词：「画后端查询与预测接口的 mermaid 时序图，参与方为前端/接口层/MySQL/模型注册表，体现鉴权、校验与幂等落库」

## 图 4：后端模块类图（§五·类图，课程点名）

```mermaid
classDiagram
    class main {
        +create_app() FastAPI
        +_lifespan()
    }
    class config {
        +DATABASE_URL
        +API_TOKEN
        +MODEL_DIR
        +FEATURE_COLUMNS
        +HIGH_RISK_THRESHOLD
    }
    class db {
        +get_engine()
        +init_db()
        +SessionLocal
    }
    class models {
        Commit
        CommitLabel
        CommitFeature
        Prediction
        INDEX_ASSERTIONS
    }
    class auth {
        +require_api_key()
    }
    class errors {
        +AppError
        +register_error_handlers()
    }
    class model_registry {
        +load_models()
        +default_model()
        +version_key()
        +predict_proba()
        +explain()
    }
    class api_commits {
        +list_commits()
        +commit_detail()
    }
    class api_trends {
        +trends()
    }
    class api_predict {
        +predict()
    }
    main --> api_commits
    main --> api_trends
    main --> api_predict
    main --> db
    api_commits --> auth
    api_commits --> models
    api_commits --> model_registry
    api_predict --> model_registry
    api_predict --> models
    model_registry --> config
    db --> models
    api_commits ..> errors
```

> 生成方式：Qoder（LLM）｜提示词：「按 backend/app 下模块文件画后端线 mermaid classDiagram，体现类职责与依赖方向」

## 变更日志

| 日期 | 版本 | 变更人 | 主要变更 |
|---|---|---|---|
| 2026-10-11 | 1.1 | 吕建江 | **四图唯一源码收口（PR #64，审阅选项 1）**：以含流程图的四图组替换 #55 版（#55 版缺课程点名的流程图，且标注行非原始生成记录）；#55 的两张拆分时序图内容已并入图 3；时序图默认模型口径订正为版本序 version_key（design D6）；补唯一源码声明与转换要求 |
| 2026-10-11 | 1.0 | 蒋励 | #55 重组时初版入库 |
