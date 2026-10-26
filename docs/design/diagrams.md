# 核心设计图与图源登记（共 14 张）

> 课程硬要求：设计文档须含**架构图 / 流程图 / 时序图 / 类图**，且**所有 AI 生成的图，图旁必须记一行**「生成方式：<工具名+模型> ｜ 提示词：<原样粘贴>」。
> **本文件是仓库侧唯一的图源登记表**；主交付物为飞书《产品设计文档》，图块内嵌于该文档对应章节。后端线的四张 Mermaid 源码见 §2（与飞书 5.1.2 同源，改一处须同步另一处）。
> 同名图的另一处出现位置：`backend/implementation.md`（后端线自用视图，图注与本节同源）。

## 1. 图源登记总表（14 张）

| # | 图名 | 飞书《产品设计文档》位置 | 载体 | 生成方式 | 提示词 |
|---|---|---|---|---|---|
| 1 | 端到端数据流图 | 四、概要设计（4.1 前） | `hi_flow_e2e.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「依据 data-pipeline ①~⑨ 全链路，画从仓库克隆、抽取、SZZ、特征、切分、训练、预测到 API 与前端的端到端数据流」 |
| 2 | 接口调用关系图 | 四、概要设计（4.1 前） | `hi_flow_api.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「依据接口清单与三页面映射，画前端三页面经 X-API-Key 调四个 API 端点、后端读 MySQL 并实时调模型的关系」 |
| 3 | 三层架构图 | 4.1 系统架构 | `hi_arch_3layer.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「画 JIT 缺陷预测系统三层架构图，标出可视化层 / API 层 / 数据模型层的组件、调用方向与外部依赖」 |
| 4 | 数据库 ER 图（鸦爪法，含四表字段） | 4.4 数据库概要设计 | 飞书 Mermaid 画板 `S0RDwFdPOh4toLbo5l2c65dXn5f` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 飞书画板渲染） | 「依据 `design/data-fields.md` v1.4 与 `model/feature-columns.md`，生成 erDiagram：commit / commit_label / commit_feature / prediction 四表，标主键、外键与基数」 |
| 5 | predict 核心流程图 | 5.1.2 核心流程图 & 时序图（后端线） | `predict_flow_final.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「按契约三 v1.4 错误路径与 change backend-db-and-query-api 的 predict 流程，画后端核心流程图，含全部分支判定与错误码（40100 / 40001 / 40400 / 50000，以 5.1.4 错误码表为准）」 |
| 6 | 查询与预测接口时序图 | 5.1.2 核心流程图 & 时序图（后端线） | `hi_seq_query_predict.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「画后端查询与预测接口的 mermaid 时序图，参与方为前端/FastAPI/MySQL/模型注册表，体现鉴权、校验、查询与预测分支及幂等落库」 |
| 7 | 后端核心类图 | 5.1.2 核心流程图 & 时序图（后端线） | `hi_class_backend.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「画后端核心类图：鉴权中间件、提交/趋势/预测三个路由、模型注册表、预测仓储，标出依赖关系」 |
| 8 | 图1 数据库 ER 图（鸦爪法） | 5.2 数据库表的设计 | `hi_er_db.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「画 commit / commit_label / commit_feature / prediction 四表 ER，标主键/外键与基数，鸦爪法，与契约 data-fields 同源」 |
| 9 | 图2 入库链路图 | 5.2 数据库表的设计 | `hi_flow_ingest.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「画数据线 01~04 产出 CSV 与实时同步写入 MySQL 四张表、接口读取并实时推理的链路」 |
| 10 | 模型线数据链路流程图 | 5.4.1.2 流程图 | 飞书 Mermaid 画板 `KuxMw2VXmh7EhmbLCmBc2NHrnJb` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 飞书画板渲染） | 「按 `model/data-pipeline.md` 的九步链路画模型线数据链路流程图：01 抽取提交 → 02 SZZ 打标 → 03 特征提取（契约二 14 项）→ 04 构建样本 → 05 时间序切分 → 06 训练 → 07 全量预测 → 08 覆盖矩阵 → 09 校准阈值，每步标出产物文件名，并注明仓库固定版本 camel-4.23.0」 |
| 11 | 模型线核心类图 | 5.4.1.3 类图 | 飞书 Mermaid 画板 `J6Odw946jhQArcbs9Y5c0OSBnEg` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 飞书画板渲染） | 「画模型线核心类图：Commit（提交）、SzzLabel（打标结果）、CommitFeature（14 项特征）、Prediction（预测结果）四个类，标出字段与类型，并按契约一 data-fields 标注主键 / 唯一键与关联基数」 |
| 12 | 前后端时序图 | 5.4.1.4 时序图 | 飞书 Mermaid 画板 `Oi2AwfflBh2m4ubQ6EMcj6LRnRg` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 飞书画板渲染） | 「画前端三页面与后端 FastAPI、模型模块、MySQL 之间的时序图，体现 GET /api/commits、GET /api/commits/{hash}、GET /api/trends、POST /api/predict 四条链路，含 X-API-Key 鉴权、参数校验与预测结果幂等落库」 |
| 13 | 三页面流程图 | 5.4.2.2 三页面流程图 | `03-三页面流程图.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「画前端三页面流程图：风险列表经 GET /api/commits 取数，点击行带 commit_hash 跳提交详情，提交详情经 GET /api/commits/{hash} 取数，再跳趋势看板经 GET /api/trends 取数，标出页面跳转方向与数据来源」 |
| 14 | 前端时序图（页面 ↔ 后端） | 5.4.2.3 时序图（页面 ↔ 后端） | `04-时序图.png` | CodeBuddy（DeepSeek-V4.1-Flash；Mermaid → 无头浏览器渲染） | 「画前端页面与后端 FastAPI、模型层的时序图：打开列表或详情时携带 X-API-Key 请求 /api/commits，后端返回 code=0 与 items，点击某行取 commit_hash 后返回 features 与 explanation，最后请求 /api/trends」 |

> **口径说明（已定稿）**：
> 1. 「工具名+模型」统一写为 **CodeBuddy（DeepSeek-V4.1-Flash）**。渲染方式两种：**飞书画板**（Mermaid 内联，`<whiteboard type="mermaid">`）与**无头浏览器**（Mermaid 渲染后导出 PNG）。
> 2. **改模型名须同时改四处**：《产品设计文档》14 处 +《产品需求文档》3 处 + 本表 18 处 + `backend/implementation.md` 4 处。四处不同源即视为**规格与实现不一致**缺陷。
> 3. 图 1/2 与图 3 编号来自文档早期版本；5.2 的「图1 / 图2」是文档内的局部编号，二者不冲突，**不要跨章节引用编号**。
> 4. PRD 6.2 三张低保真原型图为**图片**（`05/06/07-低保真原型-*.png`），非 Mermaid，渲染走「线框图生成 → PNG」路径，已补图源标注。


## 2. 后端线四张图（Mermaid 唯一源码，#64 收口版）


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
        D3[历史索引仓库 SOURCE_REPO（Apache Camel blobless 克隆）]
    end
    P1 & P2 & P3 -->|HTTP + X-API-Key| A1
    A1 --> A2 --> A3 & A4
    A4 --> A5 --> D2
    A3 --> D1
    A4 -->|幂等落库| D1
    D3 -->|实时同步落库| D1
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
        +DB_HOST/DB_USER/DB_PASSWORD
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
