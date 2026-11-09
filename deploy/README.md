# 工程化与容器化交付说明（DS-1）

一键启动「前端 + 后端 + MySQL」全栈；模型/特征可插件式扩展，不改核心逻辑。

## 一键启动

```bash
# 仓库根目录
docker compose up --build
```

- 前端：http://localhost:8080
- 后端：http://localhost:8000/api/health
- MySQL：localhost:3306（库 `jit_demo`，账号 `jit` / 口令 `jit`，仅本机演示）

验收自检：

```bash
curl http://localhost:8000/api/health -H "X-API-Key: dev-token"
# 期望 {"code":0,"message":"ok","data":{"status":"...","db":"up",...}}
```

首次启动 MySQL 会用 `infra/schema.sql` 建 5 张表（仅 DDL，不含数据集）。
模型权重、历史 git 仓库、`.env`、密钥一律**不随镜像分发**（见下）。

## 环境变量清单

| 变量 | 默认 | 说明 |
|---|---|---|
| `API_TOKEN` | `dev-token` | 鉴权令牌；前端构建期注入 `VITE_API_KEY`，须一致 |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | — | MySQL 连接（compose 已注入） |
| `DB_TEST_NAME` | `jit_test` | pytest 专用测试库名 |
| `MODEL_DIR` | `data_model/pipelines/expert/models` | 在线模型目录（含 `feature_order.txt` 清单） |
| `SOURCE_REPO` | 空 | 历史 git 仓库路径；不配则 `/api/predict` 无法现算新提交特征 |
| `FEATURE_EXTRACTOR_SCRIPT` | 空 | 覆盖默认特征抽取器（插件化，见下） |
| `SYNC_ON_STARTUP` | `0` | `1` = 启动时后台同步一次最新提交 |
| `HIGH_RISK_THRESHOLD` / `MID_RISK_THRESHOLD` | `0.5` / `0.2` | 高/中风险阈值 |

## 插件式扩展

### 模型：新增一个在线模型，零核心改动

在线模型由 `MODEL_DIR` 下的 `feature_order.txt` 清单唯一决定（后端 `app/model_registry.py`
启动时按清单加载，清单缺失或列序漂移则拒绝加载）。新增模型只需两步：

1. 把 `xxx_v1.pkl`（`joblib.dump` 产物，特征宽度 = 14）放进 `MODEL_DIR`；
2. 在 `feature_order.txt` 的 `[models]` 段追加一行 `xxx_v1.pkl\t模型中文名`。

特征列序与 14 项契约见 `feature_order.txt` 的 `[feature_order]` 段；清单是
`docs/model/feature-columns.md` 的副本，两者不一致以契约为准。

### 特征：替换抽取器，零核心改动

后端现算特征的唯一入口是 `app/feature_source.py::_extractor()`，默认加载
`data_model/preparation/03_extract_features.py`。外部提供自定义抽取器时设置：

```bash
FEATURE_EXTRACTOR_SCRIPT=/abs/path/my_extractor.py
```

自定义脚本 MUST 暴露 `extract_single_commit(repo_dir, commit_hash) -> dict`，返回：

```python
{
    "commit_hash": ..., "committed_at": "YYYY-MM-DD HH:MM:SS",
    "feature_version": "v1",
    "features": {"ns": ..., "nd": ..., ..., "sexp": ...},  # 14 项，键名与顺序同契约
    "vector": [...],  # 与 features 同序的 14 维向量
}
```

不可达/非法提交抛 `ValueError`（后端映射为 40400）。14 项特征键名与顺序是冻结契约，
新增特征维度属于契约变更，走 `docs/model/feature-columns.md` 升版流程，不在本插件机制内。

## 交付边界（DS-1 约定）

- 不含：模型权重（`.pkl`）、数据集、`data_model/data/camel` 克隆、`.env`、任何密钥。
- 不改：业务逻辑与接口契约（`docs/api/*`、`docs/database/*`）、CI 流水线（归 sober）。
- 已知限制：容器内未挂载 `SOURCE_REPO` 时，`/api/predict` 对新提交返回 40400；
  已入库提交的查询/详情/趋势不受影响。
