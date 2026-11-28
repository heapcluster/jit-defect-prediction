# 目录分层

新增文件必须放在下列位置之一；不在表内的新目录先在本文件登记。

## 1 仓库

```text
backend/            # FastAPI 服务
frontend/           # Vue 3 前端
data_model/         # 特征、训练与离线评估
infra/              # schema.sql 与建库、交付脚本
docs/               # 设计文档
temp/               # 运行时产物与仓库克隆缓存，不提交
openspec/           # 历史规格归档，不作为实现依据
```

## 2 后端

| 目录 | 内容 |
|---|---|
| `backend/app/api/` | 每个模块一个路由文件，只做参数校验与响应组装 |
| `backend/app/services/` | 任务执行与领域逻辑 |
| `backend/app/models.py` | ORM 模型，与建表语句一致 |
| `backend/app/db.py` | 引擎与会话 |
| `backend/app/auth.py` | 会话鉴权与当前用户解析 |
| `backend/app/errors.py` | 错误码与异常处理 |
| `backend/app/schemas.py` | 请求 / 响应 Pydantic 模型 |
| `backend/app/config.py` | 环境变量读取 |
| `backend/app/main.py` | 应用入口与路由挂载 |
| `backend/app/cli.py` | 建库、创建账号等命令行入口 |
| `backend/tests/` | pytest 用例 |

## 3 前端

| 目录 | 内容 |
|---|---|
| `frontend/src/views/` | 页面组件，文件名与页面文档对应 |
| `frontend/src/components/` | 跨页复用组件 |
| `frontend/src/router/` | 路由表，与 `界面/routes.md` 一致 |
| `frontend/src/api/` | 接口封装，按模块拆分 |
| `frontend/src/styles/` | 设计令牌与全局样式 |

## 4 约束

- 新接口只加在 `backend/app/api/`，业务逻辑放 `services/`。
- 前端只通过 `src/api/` 调用接口，不在组件里直接写 URL。
- `temp/` 下的内容不提交、不随交付分发。

## 5 后端模块职责

| 目录 | 文件 | 职责 |
|---|---|---|
| `backend/app/api/` | `auth`、`datasets`、`storage`、`page_state`、`collect`、`clean`、`train`、`predict`、`evaluate`、`jobs`、`health`、`deps` | HTTP 路由、参数校验与响应组装；任务轮询与取消统一见 `约束/job-state.md` |
| `backend/app/services/` | `artifacts`、`uploads`、`jobs`、`page_state`、`storage`、`datasets`、`validation`、`platform`、`collect`、`clean`、`train`、`predict`、`explain`、`localization`、`evaluate` | 六条流程的任务编排与领域逻辑；产物统一走 `约束/artifacts.md` |
| `data_model/` | `features`、`szz`、`semantic`、`gitops`、`ml`、`metrics`、`charts` | 纯计算：Kamei 特征、SZZ 打标、CodeBERT 编码、仓库与 diff、模型训练 / 加载、指标与图表；不依赖 Web 框架与数据库会话 |

- 提交幂等补齐在 `services/datasets.py` 的 `ensure_commit`，只由数据集保存调用；不再单独保留 `services/commits.py`。
- 不提供 `X-API-Key` / `API_TOKEN` 鉴权，也不含同步、webhook、风险趋势相关模块。
- 不提供 `services/feature_extract.py` / `services/semantic_encode.py` / `services/diff.py` / `timeutil.py`：特征在 `data_model/features.py`，语义编码在 `data_model/semantic.py`，diff 在 `data_model/gitops.py` 与 `services/localization.py`。
