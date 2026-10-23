## Why

后端从 `backend/` 启动时不自动包含仓库的 `data_model/` 导入路径，使用规范包名保存的自定义模型可能反序列化失败；当前虽有异常日志，却没有一次启动的失败模型汇总。补齐导入路径与可定位的失败清单，保持契约三的启动降级和响应脱敏规则。基线已含 #96 的清单驱动加载（`feature_order.txt` 的 `[models]` 段为在线模型唯一来源），本 change 不推翻该语义，只在其之上叠加导入路径与失败汇总。

## What Changes

- 在加载权重前，将由 `app.config.REPO_ROOT` 推导的可信 `data_model/` 绝对路径加入 `sys.path`，重复加载不重复插入；不从请求参数或 `MODEL_DIR` 动态引入代码路径。
- 汇总清单已声明但文件缺失、反序列化失败或特征宽度不符的模型名，以 `logger.error` 输出失败清单；保留成功清单与单文件异常详情，失败不阻断其它模型加载。清单本身缺失或列序漂移时沿用 #96 的整目录拒绝语义，不伪造失败名单。
- `backend/.env.example` 注明 MODEL_DIR 留空时使用 `data_model/pipelines/expert/models/`，原有本地 `.env` 不改动。
- 在 `backend/tests/test_integration_*.py` 建立可运行的 SQLite 建表、四类 CSV 灌入、四接口及幂等验证，不依赖真实 MySQL 或外部权重。
- D-09 按用户最新要求另开独立 change；保留 `docs/repo/defect-records.md` 的 P3登记，不在本次模型加载修复中修改哈希大小写语义。
- 定位：在 #96 已合并的清单加载之上补导入路径与失败汇总，不改清单解析、不动 `[models]` 白名单范围与列序校验。不做：不修改模型导出格式、不注册 `__main__` 兼容别名、不修改前端或训练代码、不做 MySQL 灌库、不新增接口/健康检查/在线特征抽取。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `predict-api`：新增独立 requirement，明确仓库模型模块解析路径与失败模型汇总；保留既有模型加载 requirement，避免与 PR #82 的默认路径修订重叠。

## Impact

- 代码：`backend/app/model_registry.py`、`backend/.env.example`。
- 测试：`backend/tests/test_model_registry.py`、`backend/tests/test_integration_api.py`；不改 `backend/tests/conftest.py`（#96 已为其模型目录写好清单），集成夹具自建独立 SQLite engine、临时权重与 `feature_order.txt`，复用已有类型和令牌，不写真实凭据。
- 依赖：不新增，依赖清单仍以 `data_model/environment.yml` 为准。
- 规格：只新增 `predict-api` requirement；不修改 `docs/backend/api-spec.md`、契约一/二或 `docs/design/sprint0-scope.md` 边界。
- 交付边界：T9最终目标是指定八模型全部可用、逐个POST返回真实非空解释；本PR先交付用户指定的导入路径与失败汇总小修，不缩减模型数量，也不将失败汇总或SQLite fixture测试等同T9通过。八模型加载、解释器覆盖与MySQL证据仍列未完成。
- 已核实限制：当前本机 `tabnet_v1.pkl` 引用 `__main__.TabNetWithEarlyStop`。仅设置 `sys.path` 的独立进程仍抛 `AttributeError`；需要模型线重新导出为可导入类路径，或另行明确兼容方案，不能把本 change 描述为已修复该旧权重。
