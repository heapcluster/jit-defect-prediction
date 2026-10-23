# backend-model-load-paths — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/predict-api/spec.md`
> 负责人：backend 吕建江 ｜ 创建：2026-10-23 ｜ 状态：进行中（7/9；实现与SQLite验证完成，PR #99已创建，真实环境验收待收口）
> 用户故事：无（工程化）；支撑契约三 POST /api/predict 与四接口 SQLite 联调
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块。

## 1. 模型加载与配置说明

- [x] 1.1 `load_models()` 加入由 REPO_ROOT 推导的 data_model 导入路径，重复调用不重复插入 — 交付物：`backend/app/model_registry.py`；独立消费者进程加载规范模块路径模型通过。
- [x] 1.2 汇总反序列化失败与宽度不符的模型名，输出 ERROR 日志并保留成功清单 — 交付物：`backend/app/model_registry.py`；损坏文件不阻断有效模型，测试见§1。
- [x] 1.3 `.env.example` 补 MODEL_DIR 默认目录说明，不填写真实令牌/密码、不改本机 .env — 交付物：`backend/.env.example`。

## 2. 测试与回归

- [x] 2.1 补独立进程导入、路径幂等、损坏文件、宽度拒收、空失败清单与主模块类失败测试 — 交付物：`backend/tests/test_model_registry.py`；新增6条，消费者未预导入自定义模型类，包含独立__main__坏导出反例。
- [x] 2.2 新增独立 SQLite 集成夹具及四接口流程测试，四类 CSV 各灌两遍、重复 predict 不增行、空数据与缺特征按契约返回 — 交付物：`backend/tests/test_integration_api.py`，6条全过；未接触真实数据库。
- [x] 2.3 增加无令牌/畸形参数/加载失败响应脱敏断言，跑 targeted 与后端全量测试 — 交付物：上述测试；定向17 passed、全量112 passed，记录见§5。

## 3. 审阅与跨线交付

- [x] 3.1 严格校验单 change 和全量规格，逐场景核对并提交独立 PR — 交付物：PR #99（https://github.com/heapcluster/jit-defect-prediction/pull/99），实现提交 `c920e50`；已请求苏哲勋审阅，未合入，不代表T9验收完成。
- [ ] 3.2 向模型线蒋励说明当前 TabNet 权重的 __main__ 导出问题并核验重新导出结果 — 交付形式：PR 中的复现条件与模型交付回执；本机真实权重复验仍7/8，此项不得勾选。
- [ ] 3.3 2026-10-24 按已授权环境补实际模型 API 与 MySQL 证据 — 交付给 backend 吕建江；包括T9逐个model_name请求、非空真实解释、幂等与性能。未执行前只报告SQLite结果。

## 测试与验证（强制板块）

> 命令使用按 `data_model/environment.yml` 建好并激活的 Python 3.12 环境；本次实际解释器版本3.12.15。严格校验与SQLite结果不代表T9完整通过。

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | model_registry.load_models 的路径、注册表与失败日志 |
| 测试文件 | `backend/tests/test_model_registry.py` |
| 用例数与结果 | 11条（既有5条、新增6条），与集成文件合跑17 passed |
| 复现命令 | cwd=backend：`python -m pytest tests/test_model_registry.py tests/test_integration_api.py` |
| 正向 | 独立生产者按包路径保存、独立消费者加载；调用两次仅一条路径；路径来自repo而非外部权重目录 |
| 异常/边界 | 损坏文件、非14维与__main__坏导出被拒并汇总；恢复正常文件后旧失败清单不残留；缺失目录清空注册表 |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | SQLite建四表 → 四类CSV灌入 → 模型注册 → GET列表/详情/趋势与POST预测 |
| 测试文件 | `backend/tests/test_integration_api.py` |
| 用例数与结果 | 6条通过（包含在定向17条与全量112条内） |
| 复现命令 | cwd=backend：`python -m pytest tests/test_integration_api.py` |
| 关键断言 | 四类CSV重复灌入行数不变；重复预测复合键只一行且值更新；真实fixture模型SHAP非空；列表/详情读到新预测；week/month与闭区间计数一致；无数据不是404；缺特征POST为40400 |

### 3. 验收测试

| 场景 | 测试定位 |
|---|---|
| 规范包路径从backend加载 | `backend/tests/test_model_registry.py::test_repository_model_module_loads_in_clean_process` |
| 重复加载路径不重复 | 同上及 `backend/tests/test_model_registry.py::test_import_path_comes_from_repo_not_weights` |
| 损坏文件不阻断有效模型 | `backend/tests/test_model_registry.py::test_failed_models_summary_includes_corrupt_and_wrong_width` |
| 特征宽度拒收并汇总 | 同上 |
| 全成功无失败汇总 | `backend/tests/test_model_registry.py::test_failed_summary_does_not_persist_after_success` |
| __main__坏导出真实失败 | `backend/tests/test_model_registry.py::test_main_module_model_is_reported_without_alias` |
| HTTP不泄露加载异常 | `backend/tests/test_integration_api.py::test_auth_validation_and_failed_load_do_not_leak` |

本 change 的7个Scenario均有测试覆盖；T9八模型真实联调仍未通过。复现：cwd=backend `python -m pytest tests/`；cwd=仓库根 `openspec validate backend-model-load-paths --strict`、`openspec validate --all --strict`。证据见本文件§5与PR描述。

### 4. 非功能验证

| 维度 | 是否触及 | 证据与命令 |
|---|---|---|
| 性能 | 不承诺改善，不缩减加载集 | 启动耗时、RAM及8模型P95未测，不由pkl磁盘大小推算RAM |
| 安全 | 是 | 集成测试覆盖四路由缺令牌、畸形参数与无模型50000；响应无堆栈/本地路径 |
| 可靠 | 是 | 有效模型不受损坏模型影响；失败汇总只输出当次失败名称 |
| 易用 | 是 | `.env.example` 已说明默认expert/models路径；未改本机配置或前端 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划 |
|---|---|---|---|
| PR审阅与合入 | PR #99已创建并请求审阅，尚未合入 | backend 吕建江 + 苏哲勋 | 等待PR自身CI和非作者审阅；不把创建PR当成T9验收 |
| T9仍未达标：当前TabNet权重仅加路径仍失败 | 权重引用__main__.TabNetWithEarlyStop；本改动不做任意主模块别名 | model 蒋励 + backend 吕建江 | 可导入重新导出后独立进程复验；不能删模型或报7/8达标 |
| 八模型逐个POST非空解释与P95 | 路径修复不等于新增非线性SHAP支持；fixture非空不代替真权重验证 | backend 吕建江 | 后续补真正解释器及八模型证据，不返回伪造非空值 |
| MySQL建表、灌库和幂等实测 | 本轮按要求只跑SQLite | backend 吕建江 | 2026-10-24隔离环境实跑 |
| D-09独立change | 用户最新要求另开，不与模型导入小修混合 | backend 吕建江 | 后续单独change统一GET/POST小写查库；现P3记录不等于修复 |

#### 本轮执行证据

- 基线：`eea910eba80e74608c2da34e88c390879c4e0b14`；工作树 `D:/TeamWork/jit-backend-model-load`，2026-10-23，Windows 11。
- Python：`C:/Users/simple/anaconda3/envs/jit-defect-prediction/python.exe`，3.12.15；pytest 9.1.1、SQLAlchemy 2.0.54、FastAPI 0.141.1、joblib 1.6.0、ruff 0.16.8。
- cwd=backend：`python -m pytest tests/test_model_registry.py tests/test_integration_api.py` → `17 passed, 15 warnings in 2.86s`；`python -m pytest tests/` → `112 passed, 15 warnings in 5.03s`。
- cwd=仓库根：`python -m ruff check backend/app/model_registry.py backend/tests/test_model_registry.py backend/tests/test_integration_api.py` → `All checks passed!`；单change strict → valid；全量strict → `Totals: 20 passed, 0 failed (20 items)`。
- 15条警告均为FastAPI/Starlette和matplotlib/pyparsing依赖弃用提示，未禁用警告或绕过检查。
- 真实权重只读验证：cwd=backend，MODEL_DIR设为本机可信八模型目录后执行 `python -c "from app import model_registry; model_registry.load_models(); print(sorted(model_registry._REGISTRY))"`，成功名称为 et_v1/lgbm_v1/lr_v1/mlp_deep_v1/rf_v1/svm_v1/xgb_v1，汇总为 `failed models: ['tabnet_v1']`，异常 `AttributeError: Can't get attribute 'TabNetWithEarlyStop' on __main__`。此测试不连接或修改数据库，不能作为8/8通过证据。
