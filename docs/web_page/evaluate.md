# 性能评估工具台（Evaluate）

实现状态：已实现　期次：一期

## 一句话

独立评估工具：上传或从产物库选择 `predictions.csv`（CSV/XLSX，可选第二输入 `labels.csv`）；已导入数据集仅作额外便利选择。设阈值 slider、勾选指标、指定主排序后运行 job；一次运行产出一版结果，改配置再运行产新一版，结果版本列表可切换查看；产出 metrics/confusion/报告/图 + manifest，可下载；图件与 manifest 可选登记入库（model_figure），供展示层 figures 接口读取。

## 入口与导航

- 本页为功能⑥（预测性能评估）tab「评估」，路由 `/evaluate`；页内子签为「评估工具台」与「模型性能」，后者保留已有模型指标与图件展示，入口 `/evaluate?section=models`。旧 `/model-performance` 重定向到该子视图并保留其他 query 与 hash，导航见 [README.md](README.md)。
- 本页是评估计算与结果版本查看入口；展示层经 `GET /api/figures` 读取本页登记入库的图件与指标只读投影（见 [../api/figures.md](../api/figures.md)）。
- CLI 与本页调用同一评估服务，指标公式单源；页面不手工拼指标、不自行阈值重算。
- 输出文件契约：[../file-contracts.md](../file-contracts.md) §3.4/§3.5（输入）、§3.6（metrics/confusion/report/图）、§3.9（manifest）。

产物选择与下载再提交统一遵循 [公共流程](../api/README.md#产物库选择与上传等价)：预测文件取自 predict_batch，下载文件及 manifest 后以 `files[]` 提交。外部 labels 可直接上传；已导入数据集仅作额外便利选项。

## 线框图

```
┌─ 性能评估工具台 ────────────────────────────────────────────────────────┐
│ ── 输入区 ──                                                            │
│ ┌────────────────────────────────────────────────────────────┐         │
│ │ 拖拽上传 CSV/XLSX（predictions.csv §3.4，可含标签列）       │         │
│ │ 或选产物库文件 [▾ predict_batch]                            │         │
│ └────────────────────────────────────────────────────────────┘         │
│ 第二输入（可选） [拖拽 labels.csv §3.5]（predictions 已含标签时可省略）  │
│ ── 配置区 ──                                                            │
│ 阈值 slider  0 ├────────●────────┤ 1   当前 [0.5]  [恢复默认]           │
│ 指标 [☑AUC ☑AP ☑F1 ☑Precision ☑Recall ☑Accuracy                         │
│       ☐Recall@20 ☐Recall@50 ☐P_norm ☐Popt]（清单来自接口）              │
│ 主排序 [▾ AUC]（须属于勾选集合）                                         │
│ [运行]                                                                  │
│ ── job 进度 ──                                                          │
│ 状态[运行中] [██████░░░░] 模型 1/2   [日志] [重试] [取消]               │
│ ── 结果版本列表 ──                                                      │
│ [●v3 阈值0.3 2026-11-21] [○v2 阈值0.5 …] [○v1 …]  ← 切换查看历史版本    │
│ ── 输出区（当前选中版本）──                                             │
│ 元信息：阈值[__] 样本数[n] 正样本率[__%] 数据集版本[__] 模型版本[__]     │
│ metrics.csv 预览（长表） schema 提示：§3.6                               │
│ │ model_name  line  metric  value  threshold  n  pos_rate … │           │
│ confusion.csv 预览 │ TP __ FP __ │ FN __ TN __ │                        │
│ 图缩略图（鉴权 fetch） ┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐            │
│                        │ROC ││PR  ││混淆││校准││effort││特征重要│      │
│                        └────┘└────┘└────┘└────┘└────┘└────┘            │
│ 报告预览（md/html：指标表+混淆+图引用+不可用原因清单）                   │
│ 下载 [CSV] [XLSX] [manifest] [报告] [图 png]                            │
│ [导入库]（图件+manifest 登记 model_figure，figures 接口可见本版本）      │
└─────────────────────────────────────────────────────────────────────────┘
```

图中数值均为占位示意。

## 控件与接口映射

| 控件 | 端点 | 说明 |
|---|---|---|
| 预测文件上传 / 产物库 / 已导入数据集（便利） | 产物查询 `GET /api/jobs?kind=predict_batch`，经 `/api/predict/outputs/{job_id}/{name}` 下载文件及 manifest 后按 `files[]` 提交 `POST /api/evaluate/run`；数据集便利选项 `GET /api/datasets` | predictions 必需，labels 按标签完整性可选；数据集便利选择不等同于产物库 |
| 第二输入 labels.csv | `POST /api/evaluate/run`（multipart 第二文件） | 按 hash join；冲突以 labels 为准，冲突数入 manifest（§3.5） |
| 阈值 slider / [恢复默认] | `POST /api/evaluate/run`（`threshold`）；`GET/PUT /api/config`（`decision_threshold`） | 开区间 (0,1)；恢复默认 = 删用户键回退出厂值 |
| 指标勾选 / 主排序 [▾] | `GET /api/evaluate/metrics`（清单与定义）；`PUT /api/config`（`metrics_selected` / `primary_metric`） | 清单接口读取，前端不写死；主排序须属勾选集合 |
| [运行] | `POST /api/evaluate/run` | 返回 `job_id`；一次运行 = 一版结果，改配置不自动重算 |
| 进度条 / [日志][重试][取消] | `GET /api/jobs/{id}`；`POST /api/jobs/{id}/retry\|cancel` | 五态 |
| 结果版本列表 | `GET /api/jobs?kind=evaluate`（历史成功 job 即版本） | 点选版本 → 按该 `job_id` 取 outputs 渲染，配置快照随版本展示 |
| metrics/confusion 预览 / [CSV][XLSX] | `GET /api/evaluate/outputs/{job_id}/evaluate_metrics_{job_id}.csv`、`evaluate_confusion_{job_id}.csv`（`format=xlsx`） | schema §3.6；多模型长表按主排序指标降序 |
| 图缩略图 / [图 png] | `GET /api/evaluate/outputs/{job_id}/{name}.png` | roc/pr/confusion/calibration/effort/feat_importance；fetch 带 `X-API-Key` 转 ObjectURL，卸载释放 |
| 报告预览 / [报告] | `GET /api/evaluate/outputs/{job_id}/evaluate_report_{job_id}.md`（html 可选） | 含不可用原因清单 |
| [manifest] | `GET /api/evaluate/outputs/{job_id}/{name}.manifest.json` | 阈值/指标/主排序配置快照 + 输入输出 checksum |
| [导入库] | `POST /api/storage/import` | 仅图件与 manifest 登记 model_figure；metrics/confusion/report 无表映射不入库（见 [../api/storage.md](../api/storage.md)） |

## 交互流程

1. 上传 `predictions.csv`（CSV/XLSX），或选择 predict_batch 的历史产物，下载文件及 manifest 后以 `files[]` 提交；已导入 dataset_id 另作便利输入。已含可用真标签时可省略 labels，否则另传 labels 按 hash join，冲突以 labels 为准并登记数量。
2. 拖阈值 slider（开区间 (0,1)，越界即 40001 提示）；[恢复默认] 回退出厂 0.5；勾选指标（清单来自 `GET /api/evaluate/metrics`，含 effort-aware 指标）；指定主排序（须属勾选集合）。
3. [运行] 调 `POST /api/evaluate/run`（multipart）→ 返回 `job_id` → 轮询 `GET /api/jobs/{id}`；运行期间改配置不影响本次 job（配置快照已入 manifest）。
4. 成功后本 job 成为新一版结果，追加进结果版本列表并自动选中；输出区渲染元信息（阈值/样本数/正样本率/数据集版本/模型版本）+ metrics 长表预览 + confusion 预览 + 六类图缩略图（鉴权 fetch）+ 报告预览。
5. 切换版本列表中的历史版本 → 按该版本 `job_id` 重新取 outputs 渲染；每版自带配置快照，版本间互不覆盖。
6. 改配置后再次 [运行] 产新一版；页面不提供配置变更即自动重算的行为，结果永远对应某次显式运行。
7. 下载 [CSV]/[XLSX]/[manifest]/[报告]/[图 png]；多模型输入时同一视图比较，按主排序指标降序。
8. 可选 [导入库] 调 `POST /api/storage/import` 登记本版本图件与 manifest，提示「展示层 figures 接口可见本版本」；失败展示 `error_log` 脱敏文案 + [重试]。

## 空态与错误

- 三态：加载中 / 空（库空时下拉提示「暂无可选项，可直接上传」；无历史版本时版本列表显示「运行后生成第一版」）/ 失败（错误文案 + 重试）。
- 非法输入：缺列 / 错类型 / 公式注入 / 超大小 → 40001 明确报错，不产半成品指标。
- 评估不可用语义：缺标签 / 无预测行 / 样本数不足 / 模型与数据不兼容 → 报告与预览给明确原因码，MUST NOT 展示空数值或伪造 0。
- 阈值越界 / 主排序不属勾选集合 → 40001，原配置不变。
- 缺图降级以响应 `missing[]` 为准，不靠撞 404；effort-aware 与 effort-unaware 两类图各至少一张（课程硬要求）。
- 错误码：40001 / 40100（禁用 [运行]）/ 40400 / 50000；进程重启遗留 running 置 failed，历史成功版本不受影响。

## 验收

- 只上传 `predictions.csv`（含标签列，库空、预测模块未跑）即可完成运行并下载 metrics/confusion/报告/图 + manifest。
- 非法文件（缺列/错类型/公式注入/超大小）明确报错，不产半成品。
- 输出 CSV 用 Excel 打开中文不乱码；XLSX 可选。
- manifest 可下载且 checksum 与文件一致；阈值与指标配置快照完整。
- CLI 同参数（同输入 + 同阈值 + 同指标集）产出等价文件（fixtures：`tests/fixtures/files/evaluate/`）。
- 一次运行产一版；改阈值再运行产新版；版本列表切换查看历史版本，各版数值与其配置快照一致。
- 默认阈值 0.5 下与离线评估口径逐值一致（容差 1e-6）；阈值改 0.3 后混淆与 F1/Precision/Recall/Accuracy 变化，ROC/PR 不变。
- 勾选指标子集 + 主排序生效；≥2 模型同视图比较；缺标签等不可用场景给原因不造 0。
- [导入库] 后 `GET /api/figures` 可按模型与本版本 job_id 取到图件与指标只读投影；图全部鉴权 fetch 转 ObjectURL。