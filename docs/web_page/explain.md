# 预测解释工具台（Explain）

实现状态：已实现　期次：一期

## 一句话

独立解释工具：上传或从产物库选择 `model_package.zip` + 特征文件 `commits.csv`/`cleaned.csv`（CSV/XLSX）；可选 predictions 只用于核对，已登记模型与已导入数据集仅作额外便利选择。选 XAI 技术（SHAP/LIME）与参数、展示条数、对比开关后运行 job，产出 `explanations.csv`（§3.7）+ manifest，可下载；提交详情页经 `/api/explain` 与 predict 并行编排获取解释，不依赖本页输出入库（explanations 无 12 表映射，不提供导入库）；预测模块不在场也能跑。

## 入口与导航

- 本页为功能⑦（预测结果解释）tab「解释」，路由 `/explain`；页内为解释工具台，解释结果在输出区展示，导航见 [README.md](README.md)。
- CLI 与本页调用同一解释服务；页面不承载解释计算，切换技术走同一运行入口。
- 输出文件契约：[../file-contracts.md](../file-contracts.md) §3.3（模型工件输入校验）、§3.7（explanations.csv）、§3.9（manifest）。

产物选择与下载再提交统一遵循 [公共流程](../api/README.md#产物库选择与上传等价)：模型包取自 train，特征文件取自 collect/clean，可选预测文件取自 predict_batch，下载文件及 manifest 后以 `files[]` 提交。已登记模型与已导入数据集是额外便利选项，不代表产物文件引用。

## 线框图

```
┌─ 预测解释工具台 ────────────────────────────────────────────────────────┐
│ ── 输入区 ──                                                            │
│ 模型工件 ┌────────────────────────────────────────────┐                │
│          │ 拖拽上传 model_package.zip（§3.3）          │                │
│          │ 或选产物库模型包 [▾ train]                 │                │
│          │ 已登记模型 [▾]（额外便利选择）              │                │
│          └────────────────────────────────────────────┘                │
│ 特征文件 ┌────────────────────────────────────────────┐                │
│          │ 拖拽上传 CSV/XLSX（commits/cleaned.csv）    │                │
│          │ 或选产物库文件 [▾ collect / clean]          │                │
│          └────────────────────────────────────────────┘                │
│ 提交范围（可选） [hash 清单____ 或 全文件]                               │
│ ── 配置区 ──                                                            │
│ 技术 [▾ SHAP / LIME]（兼容矩阵来自接口，不支持组合置灰+原因）            │
│ 技术参数（随技术动态） SHAP：[背景样本数__]  LIME：[扰动样本数__ 核宽__] │
│ 展示条数 Top-N [8]   ☐ 对比开关（SHAP 与 LIME 并排）                    │
│ [运行]                                                                  │
│ ── job 进度 ──                                                          │
│ 状态[运行中] [█████░░░░░] 提交 __/__   [日志] [重试] [取消]             │
│ ── 输出区 ──                                                            │
│ explanations.csv 预览（前 20 行） schema 提示：§3.7                      │
│ │ commit_hash  technique  feature  raw_value  contribution  direction rank │
│ │ a1b2c3d4…    SHAP       ns       __         +__           increase  1    │
│ │ a1b2c3d4…    SHAP       nd       __         -__           decrease  2    │
│ 贡献条形图缩略图（鉴权 fetch，正负方向双色）                             │
│ 对比视图（开关开启时） ┌─ SHAP ─────┐ ┌─ LIME ─────┐                    │
│                        │ 特征排序表 │ │ 特征排序表 │                    │
│                        └────────────┘ └────────────┘                    │
│ 不支持组合 → reason_code 行明确展示（feature 空 / contribution 空）      │
│ 下载 [CSV] [XLSX] [manifest] [贡献图 png]                               │
│ （无导入库：explanations 无 12 表映射；详情页经 /api/explain 获取）     │
└─────────────────────────────────────────────────────────────────────────┘
```

图中数值均为占位示意。

## 控件与接口映射

| 控件 | 端点 | 说明 |
|---|---|---|
| 模型包上传 / 产物库 / 已登记模型（便利） | 产物查询 `GET /api/jobs?kind=train`，下载 zip 及 manifest 后按 `files[]` 提交 `POST /api/explain/run`；登记模型选项 `GET /api/models` | zip 校验 checksum 与特征列宽（§3.3），登记 model_name 是额外便利选项 |
| 特征文件上传 / 产物库 / 已导入数据集（便利） | 产物查询 `GET /api/jobs?kind=collect`、`kind=clean`，下载后按 `files[]` 提交；数据集便利选项 `GET /api/datasets` | CSV/XLSX 双入，特征行是必需主输入 |
| predictions（可选核对） | 直接上传，或从 `GET /api/jobs?kind=predict_batch` 选择文件，经 `/api/predict/outputs/{job_id}/{name}` 下载后加入 `files[]` | 仅核对模型版本与提交范围，不提供它也能运行 |
| 提交范围输入 | `POST /api/explain/run`（`commit_hashes[]`，缺省全文件） | 圈定解释对象 |
| 技术 [▾] / 技术参数表单 | `GET /api/explain/techniques`（技术清单 + 模型类型兼容矩阵 + 参数 schema） | 前端不写死技术清单；不支持组合置灰并给原因 |
| 展示条数 / 对比开关 | `POST /api/explain/run`（`top_n` / `techniques[]`）；缺省 `GET/PUT /api/config`（`default_xai`、`explain.compare_enabled`、`page_prefs` 展示条数偏好） | compare=true 时同 job 内跑 SHAP+LIME 两技术 |
| [运行] | `POST /api/explain/run` | 返回 `job_id`，提交即返回 |
| 进度条 / [日志][重试][取消] | `GET /api/jobs/{id}`；`POST /api/jobs/{id}/retry\|cancel` | 五态；耗时解释异步执行 |
| 预览表 / 对比视图 / [CSV][XLSX] | `GET /api/explain/outputs/{job_id}/{name}`（按已登记 CSV/XLSX 名下载，前端从 comparison JSON 读取预览） | schema §3.7；对比视图按 technique 分列同一份文件 |
| 贡献图缩略图 / [贡献图 png] | `GET /api/explain/outputs/{job_id}/{name}.png` | fetch 带 `X-API-Key` 转 ObjectURL，卸载释放 |
| [manifest] | `GET /api/explain/outputs/{job_id}/{name}.manifest.json` | 技术/参数/top_n 配置快照 + 模型与特征版本 |
| 输出复用 | 提交详情页 `POST /api/explain`（与 predict 并行编排） | explanations 无 12 表映射，不走 storage 导入（见 [../api/storage.md](../api/storage.md)） |

## 交互流程

1. 选模型：上传模型包，或从 train 产物库下载 zip 及 manifest 后按 `files[]` 提交；已登记 model_name 另作便利选择。checksum 与特征列宽校验失败即拒绝。
2. 上传待解释特征文件（CSV/XLSX），或选择 collect/clean 产物下载后提交；已导入 dataset_id 另作便利输入。可选提供 predictions 进行版本与范围核对，但只提供模型包与特征表也能运行。
3. 调 `GET /api/explain/techniques` 渲染技术下拉与兼容矩阵：当前模型线不支持的技术置灰并展示原因；选定技术后动态生成参数表单（schema 驱动）。
4. 设展示条数 Top-N 与对比开关；开启对比时本次 job 同时运行 SHAP 与 LIME，输出同一 `explanations.csv`（technique 列区分）。
5. [运行] 调 `POST /api/explain/run`（multipart）→ 返回 `job_id` → 轮询 `GET /api/jobs/{id}` 按提交推进进度。
6. 成功后输出区渲染前 20 行预览（特征/原始值/贡献/方向/排名，按 |contribution| 排序取 Top-N）+ 贡献条形图缩略图；对比开启时 SHAP/LIME 并排两表，统一视觉样式。
7. 不支持的模型×技术组合产 `reason_code` 行（feature 空、contribution 空、reason_code 非空）并在预览中明确展示，MUST NOT 静默缺行或返回空数组。
8. 下载 [CSV]/[XLSX]/[manifest]/[贡献图 png]；本模块输出无 12 表映射，不提供导入库，提交详情页经 `POST /api/explain` 与 predict 并行编排获取解释。

## 空态与错误

- 三态：加载中 / 空（库空时下拉提示「暂无可选项，可直接上传」；未选技术时 [运行] 禁用）/ 失败（错误文案 + 重试）。
- 非法输入：缺列 / 错类型 / 公式注入 / 超大小 / 特征列宽不匹配 / zip checksum 不符 → 40001 明确报错，不产半成品解释。
- 技术不可用（如深度文本模型 × LIME 不支持）→ 兼容矩阵前置置灰；运行期发现不支持产 reason_code 行，不静默降级。
- 解释超时 / 资源受限 → job failed 明确原因 + [重试]；同 (hash, model, feature_version, technique) 结果可缓存复用，缓存命中在 manifest 标注。
- 错误码：40001 / 40100（禁用 [运行]）/ 40400 / 50000；默认技术与 Top-N 落配置，重启恢复。

## 验收

- 只上传模型 zip + 特征文件（库空、预测模块未跑）即可完成运行并下载 `explanations.csv` + manifest。
- 非法文件（缺列/错类型/公式注入/超大小）明确报错，不产半成品。
- 输出 CSV 用 Excel 打开中文不乱码；XLSX 可选。
- manifest 可下载且 checksum 与文件一致；含技术/参数/模型版本/特征版本快照。
- CLI 同参数（同模型 + 同输入 + 同技术 + 同参数）产出等价文件（测试内联合成夹具，AI 生成未审核）。
- SHAP 与 LIME 在同一提交上均可生成解释，结果结构一致、可排序；对比开关开启时并排展示。
- 不支持组合产 reason_code 行并明确提示，不静默缺行；解释输出不改预测概率或标签。
- Top-N 生效；默认技术与展示偏好重启后保持；提交详情页经 `/api/explain` 获取解释，不依赖本页输出入库。