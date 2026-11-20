# 提示词：后端单元测试用例生成（接口/安全/契约）

> 用途：记录后端单元测试用例生成时使用的提示词与产出摘要，供审核与复现参考。
> 关联提交：`1d6b06c`。

## 基本信息

- 使用工具：CodeBuddy（DeepSeek-V4.1-Flash）
- 使用日期：2026-11（用例生成期）
- 关联测试文件：`backend/tests/`（28 个文件，287 条）
- 关联文档：`docs/api/`、`docs/database/commit_feature.md`、`openspec/specs/`
- 来源标注：`[AI生成-人工修改]`（AI 生成骨架，人工补充核心断言）

## 提示词原文

```text
你是 Python 后端测试工程师。为 JIT 缺陷预测系统的 FastAPI 后端编写单元测试。

业务背景：
- 系统以 Git commit 为单位预测缺陷风险，输出风险概率 [0,1]
- 统一响应包络：{code, message, data}，成功 code=0
- 错误码只用 0 / 40001（参数非法）/ 40100（鉴权失败）/ 40400（不存在）/ 50000（服务异常）
- 鉴权方式：请求头 X-API-Key，缺失或错误返回 401 + 40100
- 特征为 Kamei 14 维，列序必须与 data_model/pipelines/expert/models/feature_order.txt 一致

编写要求：
1. 用 pytest，夹具放 conftest.py；纯函数用例不得连接数据库，连库用例标 @pytest.mark.integration
2. 每个核心函数覆盖正常、边界、异常三类输入
3. 断言必须打业务语义，不要只断 HTTP 200
   - 鉴权：状态码 + code==40100 + message 文案
   - 参数校验：状态码 + code==40001，且响应体不含堆栈/SQL/本机路径
   - 概率输出：0 <= risk_score <= 1
   - 特征：列数与列序与契约逐项比对
4. 参数化用 @pytest.mark.parametrize，减少重复
5. 每个文件头加来源标注注释，格式见考核说明 §2.1

约束：
- 只写测试，不改 backend/app 下任何产品代码
- 发现的产品缺陷记录到缺陷清单，不要顺手修
```

## 大模型输出摘要

- 生成 28 个测试文件、287 条用例，按职责分组：
  - 鉴权与错误包络：`test_auth_errors.py`（3）、`test_errors.py`（4）、`test_security_boundaries.py`（50，参数化）
  - 接口层：`test_commits_api.py`（22）、`test_predict_api.py`（14）、`test_sync_api.py`（23）、`test_trends_api.py`（9）、`test_figures_api.py`（3）、`test_health_api.py`（4）、`test_integration_api.py`（5）
  - 纯函数与服务层：`test_config.py`（10）、`test_timeutil.py`（14）、`test_validate.py`（9）、`test_diff.py`（5）、`test_explain.py`（6）、`test_services_commits.py`（12）、`test_services_git.py`（9）
  - 模型注册与行级定位：`test_model_registry.py`（19）、`test_fix_suggestion.py`（3）、`test_risk_summary.py`（5）、`test_online_models.py`（10）、`test_online_inputs.py`（3）
  - SQL 契约：`test_schema_sql.py`（5）、`test_trends_sql.py`（3）、`test_db.py`（7）
- 后端全量 279 passed，行覆盖 87%

## 人工审核与修改记录

- **审核结果**：修改后采纳
- **修改内容**：
  - 补充 `test_security_boundaries.py` 的大写哈希归一化用例（D-09 口径）
  - 修正 `conftest.py` 中"所有测试依赖 MySQL"的错误表述，改为仅集成用例依赖
  - `test_online_models.py` 的维度断言改为引用 `semantic_source.DIM` 常量，避免硬编码漂移
  - 删除 `test_text_source.py` 中一条恒真断言
  - 补齐 `test_sync_api.py` 的 14 维 stub 由 `config.FEATURE_COLUMNS` 生成，不再手工同步
- **核心断言复核**：6 类口径（40100 / 40001 / 概率区间 / 14 维列序 / DSN / SZZ）已逐项与产品代码比对，7/7 一致，见 [`../README.md`](../README.md)
