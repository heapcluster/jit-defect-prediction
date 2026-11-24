# 模型预测工具台（Predict）

实现状态：已实现　期次：一期

## 一句话

独立预测工具：上传或从产物库选择 `model_package.zip` + 待预测特征文件 `commits.csv`/`cleaned.csv`（CSV/XLSX）；已登记模型与已导入数据集仅作额外便利选择。设阈值与 force_recompute 后运行 job，产出 `predictions.csv`（§3.4）+ manifest，可下载与导入库供风险列表/提交详情展示；训练模块不在场也能跑。

## 入口与导航

- 本页为功能⑤（模型预测）tab「预测」，路由 `/predict`；页内子签为预测工具台 + [风险列表](risk_list.md)（`section=risks`）+ [趋势看板](trend_board.md)（`section=trends`）。[提交详情](commit_detail.md) 使用 `/commit/:hash`，有提交对象时显示详情子签，顶级预测菜单保持高亮。旧 `/`、`/trend` 重定向到对应子视图并保留其他 query 与 hash，导航见 [README.md](README.md)。
- `/` 重定向到本 tab 的风险列表子视图，`/trend` 重定向到趋势看板子视图；`/commit/:hash` 保留并归属本 tab 的提交详情子视图，详情由风险列表行进入。
- CLI 与本页调用同一预测服务；页面不承载前向计算与阈值判定口径。
- 输出文件契约：[../file-contracts.md](../file-contracts.md) §3.3（模型工件输入校验）、§3.4（predictions.csv）、§3.9（manifest）。

产物选择与下载再提交统一遵循 [公共流程](../api/README.md#产物库选择与上传等价)：模型包取自 train，特征文件取自 collect/clean，下载文件及 manifest 后以 `files[]` 提交。已登记模型与已导入数据集是另行保留的便利选项，不代表产物文件引用。

## 线框图

```
┌─ 模型预测工具台 ────────────────────────────────────────────────────────┐
│ ── 输入区 ──                                                            │
│ 模型工件 ┌────────────────────────────────────────────┐                │
│          │ 拖拽上传 model_package.zip（§3.3）          │                │
│          │ 或选产物库模型包 [▾ train]                 │                │
│          │ 已登记模型 [▾]（额外便利选择）              │                │
│          └────────────────────────────────────────────┘                │
│ 待预测文件 ┌──────────────────────────────────────────┐                │
│            │ 拖拽上传 CSV/XLSX（commits/cleaned.csv）  │                │
│            │ 或选产物库文件 [▾ collect / clean]        │                │
│            └──────────────────────────────────────────┘                │
│ ── 配置区 ──                                                            │
│ 决策阈值 [0.5]（开区间 (0,1)）   ☐ force_recompute（忽略库中已有结果）  │
│ [运行]                                                                  │
│ ── job 进度 ──                                                          │
│ 状态[运行中] [████████░░] 已预测 __/__ 行   [日志] [重试] [取消]        │
│ ── 输出区 ──                                                            │
│ 预览表（前 20 行）  schema 提示：§3.4 predictions.csv                    │
│ │ commit_hash  model_name  risk_score  predicted_label  threshold … │  │
│ │ a1b2c3d4…    xgb_v2      0.83000     1                0.5         │  │
│ │ e5f6a7b8…    xgb_v2      0.12000     0                0.5         │  │
│ 统计：行数[__] 正预测占比[__] 缺预测行留空不填 0                         │
│ 下载 [CSV] [XLSX] [manifest]                                            │
│ [导入库]（导入后风险列表 / 提交详情页可见）                              │
└─────────────────────────────────────────────────────────────────────────┘
```

图中数值均为占位示意。

## 控件与接口映射

| 控件 | 端点 | 说明 |
|---|---|---|
| 模型包上传 / 产物库 / 已登记模型（便利） | 产物查询 `GET /api/jobs?kind=train`，下载 zip 及 manifest 后按 `files[]` 提交 `POST /api/predict/run`；登记模型选项 `GET /api/models` | 校验 checksum.sha256 与特征列宽（§3.3）；登记 model_name 不是产物文件引用 |
| 待预测特征文件上传 / 产物库 / 已导入数据集（便利） | 产物查询 `GET /api/jobs?kind=collect`、`kind=clean`，下载后按 `files[]` 提交；数据集便利选项 `GET /api/datasets` | CSV/XLSX 双入；特征列宽须与模型匹配，产物选择不传 dataset_id |
| 决策阈值 / force_recompute | `POST /api/predict/run`（`decision_threshold` / `force_recompute`）；缺省 `GET/PUT /api/config`（`decision_threshold`） | 阈值只影响 predicted_label，不改 risk_score |
| [运行] | `POST /api/predict/run` | 返回 `job_id`，提交即返回 |
| 进度条 / [日志][重试][取消] | `GET /api/jobs/{id}`；`POST /api/jobs/{id}/retry\|cancel` | 五态；进度按行推进 |
| 预览表 / [CSV][XLSX] | `GET /api/predict/outputs/{job_id}/predict_predictions_{job_id}.csv`（`format=xlsx`） | schema §3.4；risk_score 5 位小数 |
| [manifest] | `GET /api/predict/outputs/{job_id}/{name}.manifest.json` | 输入 checksum + 模型版本 + 阈值快照 |
| [导入库] | `POST /api/storage/import` | 按 (commit_hash, model_name) 自然键幂等 upsert 入 prediction 表 |

## 交互流程

1. 选模型：直接上传模型包，或从 train 产物库下载 zip 及 manifest 后按 `files[]` 提交；已登记 model_name 另作便利选择。校验 checksum 与特征列宽，失败时拒绝加载。
2. 上传待预测特征文件（commits/cleaned，CSV/XLSX），或选择 collect/clean 产物下载后按 `files[]` 提交；已导入 dataset_id 另作便利选择。校验 schema 与模型输入匹配（expert 14 / semantic 768 / fused 782 / e2e 文本）。
3. 设决策阈值（缺省读 `GET /api/config`）与 force_recompute：不勾选时库中同 (hash, model, 版本) 已有结果可沿用并在 manifest 标注沿用行数；勾选则全部强制重算。
4. [运行] 调 `POST /api/predict/run`（multipart）→ 返回 `job_id` → 轮询 `GET /api/jobs/{id}` 展示按行进度。
5. 成功后输出区渲染 `predictions.csv` 前 20 行预览 + §3.4 schema 提示 + 统计；透传 `is_bug_inducing` 空值显示「未打标」，缺预测行留空，MUST NOT 填 0。
6. 下载 [CSV]/[XLSX]/[manifest]；输出含 model_version / feature_version / decision_threshold / predicted_at，便于追溯与过期标记。
7. 可选 [导入库] 调 `POST /api/storage/import`：幂等 upsert，不产生重复记录；成功提示「风险列表 / 提交详情页可见」；模型或特征版本变化时旧库内结果可标记过期。
8. 失败：`error_log` 脱敏文案 + [重试]；重试沿用原配置快照。

## 空态与错误

- 三态：加载中 / 空（库空时两个下拉均提示「暂无可选项，可直接上传」）/ 失败（错误文案 + 重试）。
- 非法输入：缺列 / 错类型 / 公式注入 / 超大小 / 特征列宽不匹配 / zip checksum 不符 → 40001 明确报错，不产半成品 predictions。
- 待预测文件为空集 / 模型加载失败 → 明确原因码；加载失败不影响库中已有预测结果。
- 阈值越界（非开区间 (0,1)）→ 40001，原值不变。
- 错误码：40001 / 40100（禁用 [运行]）/ 40400 / 50000；进程重启遗留 running 置 failed，可重试。

## 验收

- 只上传模型 zip + 特征文件（库空、训练/收集模块未跑）即可完成运行并下载 `predictions.csv` + manifest。
- 非法文件（缺列/错类型/公式注入/超大小）与损坏 zip 明确报错，不产半成品。
- 输出 CSV 用 Excel 打开中文不乱码；XLSX 可选。
- manifest 可下载且 checksum 与文件一致；含阈值与模型版本快照。
- CLI 同参数（同模型 + 同输入 + 同阈值）产出等价文件（fixtures：`tests/fixtures/files/predict/`）。
- 阈值改变只影响 predicted_label 列，risk_score 不变；force_recompute 勾选时全部行重算。
- [导入库] 重复导入不产生重复记录；导入后风险列表/详情页可见本次结果。
- 缺预测行与未打标标签均留空显示，不渲染 0。