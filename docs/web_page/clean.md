# 数据清洗工具台（Clean）

实现状态：已实现　期次：一期

## 一句话

独立清洗工具：上传 `commits.csv`（CSV/XLSX）或从产物库选择同类文件；已导入数据集仅作额外便利选择。编排可启停、可排序、可调参的处理链，preview/apply 两种模式运行 job，产出 `cleaned.csv`（§3.2）+ 每步统计 + 特征前后分布图 + manifest，可下载与导入库；上游收集模块不在场也能跑。

## 入口与导航

- 本页为功能③（数据清洗与预处理）tab「清洗」，路由 `/clean`；页内为清洗工具台，输出预览即展示，导航见 [README.md](README.md)。
- CLI 与本页调用同一处理链实现；特征口径复用离线脚本核心逻辑，页面不承载任何变换计算。
- 输出文件契约：[../file-contracts.md](../file-contracts.md) §3.2（cleaned.csv + steps_stats.json + 分布图）、§3.9（manifest）。

产物选择与下载再提交统一遵循 [公共流程](../api/README.md#产物库选择与上传等价)：选择来源任务文件，下载文件及 manifest 后以 `files[]` 提交。`GET /api/datasets` 只提供已导入数据集的额外便利选择，不代表产物库。

## 线框图

```
┌─ 数据清洗工具台 ────────────────────────────────────────────────────────┐
│ ── 输入区 ──                                                            │
│ ┌────────────────────────────────────────────────────────────┐         │
│ │ 拖拽上传 CSV/XLSX（commits.csv，§3.1）                      │         │
│ │ 或选产物库文件 [▾ collect / commits]                        │         │
│ └────────────────────────────────────────────────────────────┘         │
│ ── 配置区 ──                                                            │
│ 处理链（元数据来自操作注册表，↕ 拖拽排序）                                │
│ ┌───────────────────────────────────────────────────────────────────┐  │
│ │ ☑ 1 合并提交过滤   [参数▾]                                        │  │
│ │ ☑ 2 SZZ 文件标签复核 [参数▾ szz / szz_lite]                        │  │
│ │ ☑ 3 D5 排除        [参数▾]      ☐ 4 异常样本排除 [参数▾]          │  │
│ │ ☑ 5 标签校验       ☑ 6 特征对齐  ☑ 7 对数变换  ☐ 8 标准化         │  │
│ │ ☑ 9 时间序切分     [比例 70/30]（禁随机）                         │  │
│ └───────────────────────────────────────────────────────────────────┘  │
│ 指定特征 [默认全选 Kamei 14 项，至少保留 1 项]    种子 [42]              │
│ 模式 (●preview ○apply)                                                  │
│ [运行]                                                                  │
│ ── job 进度 ──                                                          │
│ 状态[运行中] [████░░░░░░] 步骤 3/9   [日志] [重试] [取消]               │
│ ── 输出区 ──                                                            │
│ 每步统计表（steps_stats.json）                                          │
│ │ 步骤      rows_before  rows_after  removed  标签分布  耗时 │          │
│ │ D5 排除   __           __          __       __        __   │          │
│ 特征前后分布图（缩略图，鉴权 fetch） ┌────┐┌────┐┌────┐                 │
│                                      │ ns ││ nd ││ …  │                 │
│                                      └────┘└────┘└────┘                 │
│ cleaned.csv 预览（前 20 行，apply 模式）schema 提示：§3.2                │
│ 下载 [CSV] [XLSX] [manifest] [steps_stats.json] [分布图 png]            │
│ [导入库]（apply 产物导入后训练页/展示页可选）                            │
└─────────────────────────────────────────────────────────────────────────┘
```

图中数值均为占位示意。

## 控件与接口映射

| 控件 | 端点 | 说明 |
|---|---|---|
| 上传 / 选择产物库文件 / 已导入数据集（便利） | 产物查询 `GET /api/jobs?kind=collect`，下载 `/api/collect/outputs/{job_id}/{name}` 后按 `files[]` 提交 `POST /api/clean/run`；数据集便利选项 `GET /api/datasets` | 产物文件与直接上传同一路径，不能用 dataset_id 代替文件引用；CSV/XLSX 归一为同一结构 |
| 处理链步骤清单（排序/启停/参数） | `GET /api/clean/operations`（注册表：输入/输出/参数/默认值/顺序约束） | 前端不写死步骤清单；顺序约束违反即前置校验 |
| 指定特征多选 / 种子 / 模式 | `POST /api/clean/run`（`features[]` / `seed` / `mode=preview\|apply`） | 特征缺省全选 Kamei 14 项，至少保留 1 项；preview 产统计与图，apply 另产 cleaned.csv |
| [运行] | `POST /api/clean/run` | 返回 `job_id`，提交即返回 |
| 进度条 / [日志][重试][取消] | `GET /api/jobs/{id}`；`POST /api/jobs/{id}/retry\|cancel` | 五态；进度按步骤推进 |
| 每步统计表 / 排除样本明细 | `GET /api/clean/outputs/{job_id}/clean_steps_stats_{job_id}.json` | rows_before/after/removed/label_dist/elapsed_ms/excluded_samples |
| 分布图缩略图 | `GET /api/clean/outputs/{job_id}/{name}.png` | fetch 带 `X-API-Key` 转 ObjectURL 渲染，卸载释放 |
| cleaned.csv 预览 / [CSV][XLSX] | 预览 `GET /api/clean/preview/{job_id}`；下载 `/api/clean/outputs/{job_id}/{name}` | 仅 apply 提供前 20 行及真实 CSV/XLSX，下载不接受 format 转换参数 |
| [manifest] | `GET /api/clean/outputs/{job_id}/{name}.manifest.json` | 处理链配置快照入 manifest（§3.9） |
| [导入库] | `POST /api/storage/import` | apply 产物导入为新数据集版本，原始数据不覆盖 |
| 命名处理链模板（步骤/种子/模式/图特征） | `GET /api/config`；`PUT /api/config/clean.chain_templates` | 显式保存和选择，落库恢复，不更改历史任务配置 |

## 交互流程

1. 上传 commits 文件（CSV/XLSX），或从 collect 产物库下载文件及 manifest 后按 `files[]` 提交；已导入 dataset_id 另作便利输入。校验大小、魔数、schema、公式注入与 checksum，非法即 40001 拒绝。
2. 调 `GET /api/clean/operations` 渲染处理链：↕ 拖拽排序、☑ 启停单步、[参数▾] 展开逐步参数表单；顺序约束（如特征对齐先于对数变换）违反时即时提示。
3. 指定特征默认全选 Kamei 14 项，可调整但至少保留 1 项；清空时禁用运行并提示，后端同样拒绝空数组。设种子、选 preview/apply 模式。
4. [运行] 调 `POST /api/clean/run`（multipart：输入文件 + 处理链配置）→ 返回 `job_id` → 轮询 `GET /api/jobs/{id}` 按步骤展示进度。
5. preview 完成：输出区渲染每步统计表 + 指定特征前后直方图/箱线图缩略图（鉴权 fetch）+ 被排除样本原因与示例；不产 cleaned.csv、不写库。
6. apply 完成：在 preview 全部产物之外追加 `cleaned.csv` 预览（前 20 行 + §3.2 schema 提示）；特征顺序与特征版本保留在输出与 manifest 中。
7. 下载 [CSV]/[XLSX]/[manifest]/[steps_stats.json]/[分布图 png]；相同输入 + 相同配置重跑产出一致文件。
8. 可选 [导入库]：apply 产物经 `POST /api/storage/import` 登记为新数据集版本（原版本不动），提示训练页与展示页可选；失败展示 `error_log` 脱敏文案 + [重试]。

## 空态与错误

- 三态：加载中 / 空（无历史产物时提示「暂无产物，可直接上传」）/ 失败（错误文案 + 重试）。默认图特征为 Kamei 14 项；主动清空时提示「至少选择一个图特征」并禁用运行，不能以成功无图代替必需输出。
- 非法输入：缺列 / 错类型 / 公式注入 / 超大小 → 40001 明确报错，不产半成品；preview 失败同样不留部分统计。
- 步骤顺序约束违反 / 参数越界 / 随机切分请求 → 40001 前置拒绝，不进入运行。
- 标签全空 / 正样本比例为 0 → 运行期明确原因码（可继续但统计中标注警示），MUST NOT 伪造标签分布。
- 错误码：40001 / 40100（禁用 [运行]）/ 40400 / 50000；进程重启遗留 running 置 failed，可重试。

## 验收

- 只上传 `commits.csv`（库空、收集模块未跑）即可完成 preview 与 apply 运行并下载全部输出。
- 非法文件（缺列/错类型/公式注入/超大小）明确报错，不产半成品。
- 输出 CSV 用 Excel 打开中文不乱码；XLSX 可选且主表单 sheet。
- manifest 可下载且 checksum 与文件一致；处理链配置快照完整入 manifest。
- CLI 同参数（同处理链 + 同种子）产出等价文件（测试内联合成夹具，AI 生成未审核）。
- 每步统计表含 rows_before/after/removed/label_dist/elapsed_ms/excluded_samples；指定特征前后分布图可见且鉴权取图。
- preview 不覆盖原数据；apply 生成新版本且原始数据保留；14 维特征口径与时间序切分约束不被改变。
- [导入库] 后训练页数据集下拉可见新版本；不导入不影响文件交付。