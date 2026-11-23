# 模型训练工具台（Train）

实现状态：已实现　期次：一期

## 一句话

独立训练工具：上传 `cleaned.csv`（CSV/XLSX，`commits.csv` 亦可）或从产物库选择同类文件；已导入数据集仅作额外便利选择。多选算法并按算法库元数据动态配置逐算法超参，运行训练 job，产出 `model_package.zip`（§3.3）+ 多模型比较表 + manifest，可下载与导入库登记工件；清洗模块不在场也能跑。

## 入口与导航

- 本页为功能④（模型训练）tab「训练」，路由 `/train`；页内为训练工具台，多算法对比在输出区展示，导航见 [README.md](README.md)。
- CLI 与本页调用 `data_model/pipelines/` 同一训练实现；页面不承载训练与指标计算。
- 输出文件契约：[../file-contracts.md](../file-contracts.md) §3.3（model_package.zip）、§3.6（指标长表 schema，训练摘要复用）、§3.9（manifest）。

产物选择与下载再提交统一遵循 [公共流程](../api/README.md#产物库选择与上传等价)：选择来源任务文件，下载文件及 manifest 后以 `files[]` 提交。`GET /api/datasets` 只提供已导入数据集的额外便利选择，不代表产物库。

## 线框图

```
┌─ 模型训练工具台 ────────────────────────────────────────────────────────┐
│ ── 输入区 ──                                                            │
│ ┌────────────────────────────────────────────────────────────┐         │
│ │ 拖拽上传 CSV/XLSX（cleaned.csv §3.2 / commits.csv §3.1）    │         │
│ │ 或选产物库文件 [▾ clean / collect]                          │         │
│ └────────────────────────────────────────────────────────────┘         │
│ ── 配置区 ──                                                            │
│ 模型线 [▾ expert/semantic/fused/e2e]                                    │
│ 算法多选 [☑lr ☑rf ☑xgb ☐lgbm ☐et ☐svm ☐mlp_deep ☐tabnet]               │
│ ┌─ 逐算法动态超参（元数据驱动，随勾选生成页签）──────────────────────┐  │
│ │ [lr] [rf] [xgb]                                                  │  │
│ │ xgb：n_estimators[100] max_depth[6] learning_rate[0.1]           │  │
│ │      （类型/默认值/范围/说明由 hyperparams_schema 驱动）          │  │
│ └──────────────────────────────────────────────────────────────────┘  │
│ 划分 (●比例 训练[70]%/测试[30]% ○时间边界[________])（时间序，禁随机）  │
│ 种子 [42]   ☑ auto_register（成功后自动登记工件）                       │
│ [运行]                                                                  │
│ ── job 进度 ──                                                          │
│ 状态[运行中] [██████░░░░] 算法 2/3 当前：xgb  [日志] [重试] [取消]      │
│ ── 输出区 ──                                                            │
│ 多模型比较表（按主排序指标降序，主指标 [▾ AUC]）                         │
│ │ 模型    线     算法  超参摘要  特征版本  AUC↓  F1   子项状态 │        │
│ │ xgb_v2  expert xgb   {…}      v1        __    __   成功     │        │
│ │ rf_v2   expert rf    {…}      v1        __    __   成功     │        │
│ 工件列表：train_model_{job_id}_xgb.zip …（checksum 校验通过标记）        │
│ 下载 [比较表 CSV] [XLSX] [manifest] [model_package.zip▾ 逐模型]         │
│ [导入库]（登记模型工件，预测/解释页「选已登记模型」可见）                │
└─────────────────────────────────────────────────────────────────────────┘
```

图中数值均为占位示意。

## 控件与接口映射

| 控件 | 端点 | 说明 |
|---|---|---|
| 上传 / 选择产物库文件 / 已导入数据集（便利） | 产物查询 `GET /api/jobs?kind=clean`，或 `kind=collect`；下载对应 outputs 文件及 manifest 后按 `files[]` 提交 `POST /api/train/run`；数据集便利选项 `GET /api/datasets` | cleaned 或兼容 commits 文件可直接交付，不要求先登记数据集 |
| 模型线 [▾] / 算法多选 | `GET /api/algorithms?line=` | 清单与启用态来自算法库，前端不写死；不兼容组合前置校验 |
| 逐算法动态超参表单 | `GET /api/algorithms`（`hyperparams_schema`：name/type/default/min/max/choices/desc） | 改一行 schema 表单随之变化 |
| 划分 / 种子 / auto_register | `POST /api/train/run`（`split` / `seed` / `register` / `auto_load`） | 时间序切分禁随机；register/auto_load 默认 false，auto_load 仅 expert 自产权重 |
| [运行] | `POST /api/train/run` | 返回 `job_id`，提交即返回 |
| 进度条 / [日志][重试][取消] | `GET /api/jobs/{id}`；`POST /api/jobs/{id}/retry\|cancel` | 五态；逐算法子项状态在 job 详情 |
| 多模型比较表 / 主指标 [▾] | `GET /api/train/outputs/{job_id}/train_metrics_{job_id}.csv`；主指标 `GET/PUT /api/config`（`primary_metric`） | 摘要 CSV 列 schema 复用 §3.6 metrics 长表；指标口径与评估服务单源一致 |
| [比较表 CSV][XLSX] | `GET /api/train/outputs/{job_id}/{name}`（`format=xlsx`） | UTF-8 带 BOM |
| [model_package.zip▾] | `GET /api/train/outputs/{job_id}/train_{algo}_model_package_{job_id}.zip` | §3.3：权重 + feature_order.txt + model_meta.json + checksum.sha256 |
| [manifest] | `GET /api/train/outputs/{job_id}/{name}.manifest.json` | 配置快照（algos/超参/划分/种子）入 manifest |
| [导入库] | `POST /api/storage/import` | zip 导入模型工件表（路径/校验值/版本/特征版本）；auto_register=true 时运行成功即自动执行同一导入 |

## 交互流程

1. 上传 `cleaned.csv`（或含标签与 `is_test` 的 commits 文件），或选择 clean/collect 历史产物并下载文件及 manifest 后以 `files[]` 提交；已导入 dataset_id 另作便利输入。校验大小、魔数、schema、公式注入与 checksum，不要求先导入展示库。
2. 选模型线 → 调 `GET /api/algorithms?line=` 拉该线算法清单 → 多选 ≥1 个算法；不兼容 `(line, algo)` 组合在创建任务时即 40001 前置拒绝。
3. 每个勾选算法生成独立超参页签，控件完全由 `hyperparams_schema` 驱动；越界/类型不符即时校验。
4. 设划分（比例默认 70/30 或时间边界，时间序禁随机，保留「测试集最早时间 > 训练集最晚时间」断言）、种子（默认 42）、auto_register。
5. [运行] 调 `POST /api/train/run`（multipart）→ 返回 `job_id` → 轮询 `GET /api/jobs/{id}` 展示逐算法进度与子项状态；[日志] 读 `error_log`（脱敏）。
6. 失败隔离：单算法失败只记该子项错误，不影响其他算法产出；失败任务 MUST NOT 覆盖已有可用模型工件。
7. 成功后输出区渲染多模型比较表（模型/线/算法/超参摘要/特征版本/指标/子项状态），按主排序指标降序；工件列表展示各 `model_package.zip` 与 checksum 校验结果。
8. 下载比较表 CSV/XLSX、逐模型 zip、manifest；auto_register 勾选时成功即自动登记，否则手动 [导入库] 调 `POST /api/storage/import` 登记工件，提示「预测 / 解释页已登记模型下拉可见」，无需重启后端。

## 空态与错误

- 三态：加载中 / 空（库空时下拉提示「暂无已导入文件，可直接上传」；未勾选算法时 [运行] 禁用并提示）/ 失败（错误文案 + 重试）。
- 非法输入：缺列 / 错类型 / 公式注入 / 超大小 / 缺标签 / 特征列宽与模型线不符 → 40001 明确报错，不产半成品工件。
- 超参越界 / 划分非法（随机切分）/ 不兼容线×算法 → 40001 前置拒绝。
- 运行期失败：`error_log` 可读日志 + [重试]；进程重启遗留 running 置 failed（「进程重启中断」）。
- 错误码：40001 / 40100（禁用 [运行]）/ 40400 / 50000。

## 验收

- 只上传 `cleaned.csv`（库空、收集/清洗模块未跑）即可完成运行并下载 zip + 比较表 + manifest。
- 非法文件（缺列/错类型/公式注入/超大小）明确报错，不产半成品。
- 输出 CSV 用 Excel 打开中文不乱码；XLSX 可选。
- manifest 可下载且 checksum 与文件一致；zip 内 checksum.sha256 与权重一致。
- CLI 同参数（同数据 + 同算法 + 同超参 + 同种子）产出等价文件（测试内联合成夹具，AI 生成未审核）。
- 超参表单由 `GET /api/algorithms` 元数据驱动，前端无硬编码算法清单或范围。
- 多算法结果同表比较、按主指标排序；单算法失败不影响其他算法；失败不覆盖旧工件。
- 时间序切分断言保持；同输入同配置同种子结果可复现。
- [导入库]（或 auto_register）后工件在预测/解释页「选已登记模型」下拉可见，无需重启。