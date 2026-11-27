# 配置中心 API（config）

一句话：集中读写展示阈值、默认数据集、默认解释技术、采集协议与路径、指标选择、页面偏好等可调项，并提供键级 schema 供页面渲染；不设默认模型，不在配置层做业务计算。

配置键语义与默认值来源见后端 `config_store`；本文件覆盖全部配置键，数据存储页的配置区只展示常用全局配置五项（风险阈值 / 默认数据集 / 默认解释技术 / 页面大小），其余键仍经本 API 读写，页面展示范围见 [`../web_page/storage.md`](../web_page/storage.md)。

## 1. 职责与不负责范围

- 负责按 key 读取、批量写入、单键写入与删除，返回 `source`（factory/global/user）与更新后的值。
- 负责键级校验：类型、取值范围、枚举、跨键依赖、引用对象存在性。
- 不负责触发任务、不重算历史结果；配置变更只影响之后的读取与新建任务。

## 2. 端点契约

### GET /api/config

| 参数 | 必填 | 契约 |
|---|---|---|
| `keys` | 否 | 逗号分隔；空字符串会产生空键并返回 40001；未知键返回 40001 |

响应：

```json
{
  "items": [{"config_key": "...", "value": "...", "value_type": "str", "source": "factory|global|user", "updated_at": "2026-01-01T00:00:00Z"}],
  "schema": {"key": {"label": "...", "value_type": "...", "choices": null, "group": "..."}}
}
```

`items` 按 key 排序；`schema` 只描述键，不含值。

### PUT /api/config

JSON body（`extra="forbid"`）：

```json
{"items": [{"config_key": "decision_threshold", "value": 0.5}]}
```

`items` 长度 1..25；重复键返回 `40001`；响应 `data:{items:[...]}`。

### PUT /api/config/{key}

JSON body `{"value": ...}`，`extra="forbid"`；响应单键 `items`。未知键 40001。

### DELETE /api/config/{key}

删除用户覆盖，回落到全局或出厂值；响应 `{config_key, deleted:true, fallback_source, value}`；键未保存返回 40400。

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | 未知键、类型/范围/枚举非法、批量空或重复、跨键冲突、JSON 超过 64KiB |
| 40100 | 401 | 鉴权失败，或用户被禁用 |
| 40400 | 404 | 引用的模型/数据集未登记、键未保存、用户不存在 |
| 50000 | 500 | 未预期异常 |

## 3. 输入契约

- 值类型由键的 `value_type` 决定（str/int/float/bool/json/list）。
- 典型校验：`default_dataset` 必须 `status=ready`；`default_xai ∈ {shap, lime}`；`metrics_selected` 必须是 10 个指标键的子集且唯一；`collect.protocol_whitelist ⊆ {https, git}`；`collect.allow_roots` 必须是绝对路径且不重复；`page_prefs` 仅允许 `page_size(10/20/50/100)`、`remember_drawer`、`explain_top_n(1..100)`、`collect_branch`、`collect_mode(full|incremental)`；`localization.top_n` 恰为 `{files, lines}` 且 1..1000；`localization.weights` 结构须与默认一致且非负有限。
- `ui.background_color` 与 `ui.accent_color` 必须是 `#rgb` 或 `#rrggbb`；这两项键保留在配置表中，但前端视觉主题由 `ui.css` 设计令牌决定，不消费这两项。
- 阈值类键必须在 (0,1)；`risk_mid_threshold < risk_high_threshold`；`primary_metric` 必须属于已选指标。

## 4. 输出契约

- 只返回 JSON，不产生文件、不写 job。
- `source` 语义：`factory` 出厂默认、`global` 全局默认、`user` 用户覆盖；`updated_at` 为 UTC `Z`，无覆盖时为 null。

## 5. 可配置项

本文件即配置项清单的入口：展示阈值、默认数据集、默认解释技术、采集协议与路径、指标选择、页面偏好、界面颜色（背景色 / 主题色）、定位权重与文件大小上限。数据存储页的配置区展示高风险阈值、中风险阈值、默认数据集、默认解释技术与页面大小五项，其余键仍由本 API 提供。模型不设默认值，`.env` 只提供出厂默认，不进入配置表。

## 6. 状态持久化

- 写 `user_config` 表（全局或用户级），按 key upsert；删除即回落。
- 不做版本历史，不触发任务重跑；并发写以最后提交为准。

## 7. 验收

- 键级 schema 与校验一致，非法值稳定返回 40001。
- 跨键依赖（阈值大小、主指标归属）被拒绝。
- 引用未登记的模型/数据集返回 40400。
- 删除覆盖后读回 `source` 正确回落。

## 8. 边界

配置中心只提供参数，不提供业务逻辑；任何模块都不应把配置读成隐式运行前置，缺配置时使用出厂默认并在响应中体现 `source`。
