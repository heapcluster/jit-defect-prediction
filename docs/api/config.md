# 配置中心 API（config）

一句话：以 user_config 为唯一运行时配置源，提供全局键和模块命名空间键的读取、原子写入、单键更新与删除回退，并保证重启恢复。

实现状态：部分　期次：一期

公共鉴权与包络见 [README.md](README.md)；存储职责见 [storage.md](storage.md)。

## 1. 职责与不负责范围

- 负责配置 schema 校验、跨键约束、用户/global/出厂三级解析、立即生效、持久化和恢复默认。
- 负责所有会影响收集、清洗、训练、预测、评估、解释和定位结果的配置入口。
- 不负责保存 API Key、数据库口令、LLM Key 等敏感信息，也不承担业务计算或文件导入。
- `.env` 仅提供出厂默认和部署敏感项，不是用户配置的持久化来源。

## 2. 端点契约

### GET /api/config

查询参数 `keys` 可选，逗号分隔键名。响应 `data.items[]`；`data.schema` 提供键的 `label/value_type/group/choices`，供配置区渲染，选项取真实登记数据。固定 API Token 不携带用户身份，一期接口读取、写入与删除均归属 `global`；内部配置服务支持明确用户归属与三级回退，但不接受调用方伪造身份头。配置项字段：

| 字段 | 含义 |
|---|---|
| `config_key` | 配置键 |
| `value` | JSON 解码后的标量、数组或对象 |
| `value_type` | `float` / `int` / `string` / `bool` / `list` / `object` |
| `source` | `user` / `global` / `factory` |
| `updated_at` | 最近持久化时间，factory 可为 null |

### PUT /api/config

批量原子更新，请求 `{items:[{config_key,value}]}`。任一键未知、类型错误或跨键约束失败，整批不写。响应 `{items[]}` 为写入后的生效配置。

### PUT /api/config/{key}

请求 `{value}`，响应 `{items:[...]}`。路径 key 必须在白名单内；`models/default` 只是 default_model 的管理入口，最终写同一配置键。

### DELETE /api/config/{key}

删除当前用户行，响应 `{config_key,deleted:true,fallback_source,value}`；回退 global，再回退出厂默认。用户行不存在返回 40400。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 未知键、敏感键、类型/范围/对象 schema 错误、跨键约束失败、批量部分非法 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | 删除不存在的用户键，或引用的模型/数据集/模板不存在 |
| 50000 | 500 | 未预期存储错误，不回显 SQL 或连接信息 |

## 3. 输入契约

键与值即全部输入，无文件输入。全局键：

| 键 | 类型 | 出厂默认 | 校验与用途 |
|---|---|---|---|
| `decision_threshold` | float | 0.5 | (0,1)，预测标签与评估默认阈值 |
| `risk_high_threshold` | float | 0.5 | (0,1)，且大于 risk_mid_threshold |
| `risk_mid_threshold` | float | 0.2 | (0,1)，且小于 risk_high_threshold |
| `default_model` | string | 空 | 已登记且可用模型；空时启用公共回退规则 |
| `default_dataset` | string | 空 | 已登记 dataset_id；只作便利选择 |
| `default_xai` | string | `shap` | 已注册解释技术 |
| `metrics_selected` | list | 六项基础指标 | 元素属于 evaluate/metrics 注册表且去重 |
| `primary_metric` | string | `auc` | 必须属于 metrics_selected |
| `effort_enabled` | bool | true | 是否启用 effort-aware 评估 |
| `page_prefs` | object | `{}` | 仅白名单页面偏好，不存敏感信息 |

模块命名空间键保持本身的值类型：允许根目录与协议为 list，模板与定位权重/Top-N 为 object，批大小/TTL/重试次数/文件大小为 int，对比开关为 bool，建议来源为 list；对象内部字段按模块 schema 校验：

| 命名空间 | 键 |
|---|---|
| collect | `collect.allow_roots`、`collect.protocol_whitelist` |
| clean | `clean.chain_templates` |
| train | `train.templates` |
| predict | `predict.batch_size`、`predict.cache_ttl`、`predict.retry_max` |
| explain | `explain.cache_ttl`、`explain.compare_enabled` |
| localization | `localization.weights`、`localization.top_n`、`localization.file_size_max`、`localization.suggestion_sources` |

请求不得含额外未知键；阈值不可静默截断，布尔值不接受含糊字符串，模板中的算法/操作/技术必须存在。配置校验可以读取登记表，但业务模块运行仍不以这些表作为文件交换前置。

## 4. 输出契约

仅输出上述 JSON 配置项与删除回退结果，不生成 CSV/XLSX、报告或 manifest，也不创建 `backend/var/outputs` 目录。响应不返回部署环境变量、连接串、密钥或可逆敏感字段。

批量 PUT 的返回顺序与请求一致；GET 按 config_key 字典序返回，保证测试稳定。source 表示实际生效层级，不把 factory 默认伪装为用户已保存值。

## 5. 可配置项

本篇即配置权威。读取顺序固定为当前用户 → global → 出厂默认，解析只存在于配置服务；前端和各模块不得各维护一套优先级。

- decision_threshold 与 risk_high/risk_mid 是不同语义，不得互相替代。
- default_model 为空时，回退已加载 expert 中 version_key 最大者；default_dataset 为空不阻止文件上传运行。
- 恢复默认通过 DELETE 完成，而不是把出厂值复制到用户行。
- 所有模块命名空间键遵循相同校验、原子写入与重启恢复规则。
- W1 已提供 23 键配置读写、类型校验、风险阈值与默认模型接入。`page_prefs` 子键为 `page_size/remember_drawer/explain_top_n/collect_branch/collect_mode`；后两项为 W3 收集页面的默认分支与模式，显式保存后持久化，不覆盖已创建任务的入参，定位 Top-N 对象为 `{files,lines}`。
- W4 clean.chain_templates 由九操作注册表校验，可保存最多 30 个命名配置对象；步骤省略 enabled/params 分别使用 true/默认参数。模板按原子配置写入持久化，单次运行固化快照。W5 train.templates 由算法注册表校验（line/algos/超参/划分/种子），最多 30 个命名模板，非 expert 线模板因输入契约不支持而拒绝；W8 已注册 SHAP/LIME，default_xai 可选 shap/lime；explain.compare_enabled 控制 HTTP 多技术比较，默认 false，显式开启才生效。
- 删除当前归属行前也校验回退后的跨键约束，失败时不删除；无登录上下文删除 global 行回退出厂默认。

## 6. 状态持久化

- 每次成功写入立即落 user_config 并更新 updated_at；批量更新在单事务内完成。
- 后端、容器或进程异常关闭后重启，GET 返回原配置；运行中模块在下次读取时获得新值，已产文件仍以其 manifest 配置快照为准。
- 不创建 job，不生成输出文件。配置变化可使运行时缓存失效，但不得改写历史 job 或 manifest。
- 审计日志记录键、来源和时间，不记录敏感值；敏感键请求直接拒绝。

## 7. 验收

fixtures：`tests/fixtures/files/config/`，以 JSON 正常、边界、非法配置样例驱动接口测试。

- **正常**：批量/单键读写所有全局键与命名空间键，source 正确；重启后值、模板和页面偏好完整恢复。
- **边界**：删除用户键回退 global/factory，default_model/default_dataset 为空，缓存 TTL 为 0，阈值跨键联动均按契约执行。
- **非法**：未知键、1.5 阈值、mid≥high、primary_metric 未选、敏感键、错误对象结构、批量一个坏值均返回 40001 且原值不变；删除不存在键返回 40400。
- 修改默认模型/阈值/XAI 后相关模块使用新配置，历史 manifest 不变；接口与设置页读写一致且无密钥泄漏。

## 8. 边界

配置是各模块的运行参数来源，不是数据交换通道。模块可仅凭显式 config part 和输入文件运行；user_config 提供持久默认与便利项，数据库不可用不得改变已上传文件的 schema，也不应被用作隐式上游依赖。
