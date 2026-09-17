# 库表与查询接口

> Sprint 0 ｜ 对应飞书周报任务 7（库表与接口格式，负责人吕建江）与任务 8 的后端相关动作（字段映射核对、影响接口的待确认项收口）；做法与验收见 `docs/dev-handbook.md` §7、§8
> 起草 2026-09-17 ｜ 起草人 吕建江 ｜ 关联契约：`docs/contracts/data-fields.md`、`docs/contracts/api-format.md`（冻结 9/23）、`docs/contracts/feature-columns.md`

## Why

- 后端目录目前只有 README 与依赖清单，**没有任何可执行代码**。上游数据链路已跑通（样本集与统计已产出），前端三个页面的字段映射已在 `docs/pages.md` 成文 —— 两端都在等「表建好、接口通」。
- 接口契约 9/23 冻结。**冻结应当被实现反向验证**：三个接口若不先落成代码、用 FastAPI 自动生成的 Swagger 逐字段比对一遍，冻结就是纸面冻结，偏离会在联调时才暴露，返工成本全落在前端线。
- 库表是裁定 C 的落点：模型线交付的 `prediction_result.csv` 没有表就无处可灌（交付裁定 A+C 见 `backend/README.md`，其规格在上游 change `model-training-and-delivery`，当前在远端分支 `docs/spec/model-training-delivery` 尚未合入 `main`）。
- 鉴权方式、灌入幂等键、「有提交但无预测」的响应形态都是**不可逆的口径决定**。先写代码后补规格，口径会散落在实现细节里，换人实现就跑出不同的行为。

## What Changes

- **新增 `db-schema` 能力**：按契约一建 `commit` / `commit_label` / `prediction` 三张表（ER 图中的 `commit_feature` 见待决问题 1），字段名、类型、索引（`commit_hash` 唯一索引、`committed_at` 普通索引）逐字照契约；满足「别人 clone 后一条命令建好库」；`.env.example` 入库、`.env` 不入库。
- **新增 `query-api` 能力**：按契约三落地 `GET /api/commits`、`GET /api/commits/{commit_hash}`、`GET /api/trends` 三个接口；统一响应包络、只用 5 个错误码、令牌鉴权（40100）、输入校验（40001）、`50000` 不回显内部信息；以 FastAPI 自动生成的 OpenAPI/Swagger 作实现镜像，与契约逐字段比对。
- **契约定稿与冻结**：鉴权方式由定稿人裁定并回填契约三待确认；`docs/pages.md` 字段清单与接口响应逐字段核对，缺口清单交前端线；收刘帅华对两项影响接口待确认的反馈后，9/23 前完成契约三冻结。
- **灌入**：`prediction_result.csv` 灌入脚本（裁定 C），按 `(commit_hash, model_name, feature_version)` 幂等。

**不做什么（显式列出）**

- **不做**模型文件加载与在线推理 —— 方案 A 的 `.pkl` 加载用途（在线预测还是解释计算）待 `explanation` 算法回填后另开 change
- **不做**性能与安全证据脚本 —— 周报任务 10 另开 change；本 change 只实现鉴权与校验本身
- **不做**前端页面与图表
- **不改**契约字段名与列名 —— 核对发现的缺口一律走契约变更流程
- **不新增**第四个接口（如 `GET /api/models`）—— 模型下拉选项来源待任务 8 待确认结论，不预埋

**是否触及 `docs/sprint0-scope.md` 的边界**：**不触及**。落在该文第 2 节「做」的「接口的输入校验与鉴权」与三页面接口链路之内；不改变系统定位、不改变四条线目录边界。

## Capabilities

### New Capabilities

- `db-schema`: 按契约一建表与索引、一条命令建库、灌入预测结果与特征数据
- `query-api`: 三个查询接口、统一包络与错误码、鉴权与输入校验、Swagger 实现镜像

### Modified Capabilities

无 —— `openspec/specs/` 尚无归档产出，没有被修改的既有能力。

## Impact

| 项 | 内容 |
|---|---|
| 影响目录 | `backend/`（新增应用代码、测试、灌入与种子脚本）；`docs/contracts/api-format.md`（待确认回填与冻结）；字段缺口清单以 Issue 形式交付前端线，**不直接改 `docs/pages.md`** |
| 消费的契约 | `data-fields.md` 表一/二/三与 ER 图、`api-format.md`、`feature-columns.md`（`features` 键名）—— 字段名只读不改 |
| 新增依赖 | 以 `backend/requirements.txt` 现状为准；建库方式刻意不引入 Alembic（见 design D1），**本 change 不新增依赖类别** |
| 上游依赖 | 上游 change `model-training-and-delivery`（分支 `docs/spec/model-training-delivery`，未合入）产出的 `prediction_result.csv` 与特征表；接口自测先用种子数据，不等真实数据 |
| 下游依赖 | 前端三页面联调（刘帅华）；周报任务 10 的性能与安全证据脚本 |
| 数据边界 | `.env`、数据集、模型文件一律不入库；种子数据只进本地数据库，不入库 |

## 待决问题（9/23 冻结前必须结清）

1. **`commit_feature` 是否建表？** 手册 §7 写「建三张表」，但契约一 ER 图为四张表（含 `commit_feature`），且详情接口的 14 项特征值必须有落点。本提案暂按「建表 + 灌特征 CSV」起草；若组内裁定特征另途交付，用 change 更新删去对应条目。
2. **鉴权方式**：固定共享令牌 / JWT。本提案建议固定令牌（design D2），待定稿人（吕建江）裁定并回填契约三。
3. **「提交存在但无预测记录」的响应形态**：契约三未写。本提案建议 `code=0` 且 `risk_score`/`model_name` 为 null、`explanation` 空数组（design D3），冻结时回填契约三。
4. **方案 A（`.pkl` 加载）本期用途**：在线推理还是解释计算？待模型线回填 `explanation` 算法后定；不在本 change 范围。
