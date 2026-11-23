# 趋势查询 API（trends）

一句话：按周或月只读聚合作者提交时间、所选模型预测数和当前高风险阈值命中数，供趋势图与汇总卡使用。

实现状态：部分　期次：一期

配置见 [config.md](config.md)，展示数据来自 [storage.md](storage.md) 可选导入。

## 1. 职责与不负责范围

- 负责 ISO 周/月时间桶、提交数、高风险数、平均风险和阈值回显。
- 只读 commit 与 prediction 已导入行，聚合下推数据库；不负责预测、标签判定、评估或收集。
- 高风险阈值是展示统计参数，不回写预测，也不改变风险概率。

## 2. 端点契约

### GET /api/trends

| 参数 | 必填 | 契约 |
|---|---|---|
| `granularity` | 否 | `week`（默认）/ `month` |
| `start_time` / `end_time` | 否 | committed_at 闭区间，纯日期按公共规则展开 |
| `model_name` | 否 | 缺省读 default_model，再按公共回退规则 |
| `dataset_id` | 否 | 只统计已导入数据集成员 |

响应 `data`：

| 字段 | 含义 |
|---|---|
| `granularity` / `model_name` / `dataset_id` | 实际统计维度 |
| `threshold` | 本次 high_risk_count 使用的 risk_high_threshold |
| `series[]` | 按 period 升序的时间桶 |
| `series[].period` | ISO 周 `2024-W31` 或月 `2024-07` |
| `series[].commit_count` | 桶内该模型有预测行的提交数 |
| `series[].high_risk_count` | risk_score≥threshold 的提交数 |
| `series[].avg_risk` | 桶内 risk_score 算术均值，无数据为 null |

### 错误码

| 业务码 | HTTP | 场景 |
|---|---|---|
| 40001 | 400 | granularity、时间、dataset 或未知参数非法 |
| 40100 | 401 | 缺失或错误的 `X-API-Key` |
| 40400 | 404 | 显式 model_name 或 dataset_id 不存在 |
| 50000 | 500 | 未预期聚合错误，不回显 SQL |

## 3. 输入契约

无文件输入。只接受上述筛选；时间范围两端闭区间，周使用 ISO 周，月使用 UTC 日历年月。model_name 已隐含模型线，不另收 line。

默认模型来自 user_config.default_model，未配置回退已加载 expert 中 version_key 最大者；默认数据集仅为便利筛选。数据库没有数据时返回空 series，不调用 predict 补齐。

## 4. 输出契约

仅输出 JSON 聚合，不生成图文件、CSV 或 manifest，不创建输出目录。前端以 commit_count 为柱系列、high_risk_count 为线系列；avg_risk 可用于汇总卡。

汇总值由 series 计算：提交数与高风险数求和，平均风险按 commit_count 加权；空桶 avg_risk=null，禁止按 0 参与加权。threshold 随响应回显，确保图注可复现。

## 5. 可配置项

- risk_high_threshold 控制 high_risk_count；修改后新查询使用新值，历史 predictions 文件不变。
- default_model、default_dataset 提供缺省筛选；granularity、时间、模型和数据集可由请求覆盖。
- 周/月口径固定，page_prefs 仅保存展示偏好；`.env` 仅提供出厂默认。

## 6. 状态持久化

- 只读查询，不写表、不创建 job、不写输出文件。
- storage 导入和配置变更后结果可见；重启后相同数据与阈值返回相同 series。
- 大数据量聚合在 SQL 中完成；缓存若使用，键必须含模型、数据集、时间、粒度与阈值。

## 7. 验收

fixtures：`tests/fixtures/files/trends/`，以固定 commits/predictions 和阈值配置构造正常、边界、非法场景。

- **正常**：周/月分桶、模型/数据集/时间筛选、阈值回显和双系列数值正确，前端汇总与 series 一致。
- **边界**：跨 ISO 周年、月初月末、空桶、空 series、0/1 风险分、阈值变化和同分提交均正确处理。
- **非法**：未知 granularity、紧凑错误日期、非法 dataset/model、额外参数返回 40001/40400；查询不触发预测。
- 大表 SQL 聚合不断言整表载入内存；空库不影响任何模块上传文件独立运行。

## 8. 边界

trends 只消费展示表，不是评估工具或模块间数据源。业务模块间仍只依文件 schema 兼容；default_dataset/dataset_id 为便利筛选，数据库和上游服务均非 run 前置。
