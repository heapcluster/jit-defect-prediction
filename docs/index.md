# 文档索引

docs 按对象分包，每个包只描述一类设计。不设全局总纲；跨包重复的口径，只在「唯一真源」指定的一处维护。

## 1 分包

| 包 | 只回答 | 单篇对象 | 命名 |
|---|---|---|---|
| [功能点](功能点/index.md) | 做什么、输入输出、流程、边界、验收 | 一个功能点一篇 | `01-数据存储.md` |
| [界面](界面/index.md) | 页面结构、区域、交互、状态 | 一个页面一篇 | `数据存储页.md` |
| [接口](接口/index.md) | 端点、请求、响应、错误码、状态 | 一个模块一篇 | `collect.md` |
| [数据库](数据库/index.md) | 表、字段、约束、索引、读写方 | 一张表一篇 | `dataset.md` |
| [约束](约束/index.md) | 技术栈、目录、产物、任务、验证 | 一个主题一篇 | `job-state.md` |

设计来源见 [设计图](功能点/assets/设计图.png)。

## 2 唯一真源

| 内容 | 只在 |
|---|---|
| 功能点清单与数量、功能点到页面/接口/表的对应 | 本文件第 4 节 |
| 页面清单、路由、子页、重定向 | `界面/routes.md` |
| 跨页通用状态、空态、错误、响应式 | `界面/ui-rules.md` |
| 响应信封、通用错误码、鉴权、分页 | `接口/conventions.md` |
| 任务类型与状态流转、取消与重试、轮询 | `约束/job-state.md` |
| 枚举与值域 | `约束/enums.md` |
| 算法清单、数量与超参 | `数据库/algorithm.md` |
| 表清单与数量、表结构 | `数据库/index.md` 与各表文档（建表真源 `infra/schema.sql`） |
| 产物路径、manifest、文件交换与保留 | `约束/artifacts.md` |
| 设计原则与硬约束 | 本文件第 6 节 |

其它文档只引用、不复写。发现不一致时先改真源，再改引用方。

## 3 单篇模板

- 功能点：范围 / 输入与输出 / 流程 / 边界 / 验收
- 界面：定位 / 页面结构 / 区域与组件 / 主流程 / 状态与反馈 / 接口映射 / 响应式 / 验收
- 接口：端点 / 请求 / 响应 / 错误码 / 状态与幂等
- 数据库：用途 / 字段 / 约束与索引 / 读写方
- 约束：结论 / 适用范围 / 约束条目 / 校验方式

## 4 追溯矩阵

| 设计图功能 | 功能点 | 页面与路由 | 接口 | 主要表 |
|---|---|---|---|---|
| — 登录与多用户 | `功能点/00-登录与多用户.md` | 登录 `/login`；用户信息在 `/storage` 页头 | `auth` `page-state` | `user` `user_session` `user_config` `user_page_state` |
| ① 数据库存储 | `功能点/01-数据存储.md` | 数据存储 `/storage` | `storage` `datasets` `page-state` | `dataset` `dataset_commit` `model` `model_artifact` `algorithm` `user_config` `user_page_state` `job` |
| ② 缺陷数据收集 | `功能点/02-数据收集.md` | 数据收集 `/collect` | `collect` `datasets` `page-state` | `commit` `commit_feature` `dataset` `dataset_commit` `job` |
| ③ 数据清洗与预处理 | `功能点/03-数据清洗.md` | 数据清洗 `/clean` | `clean` `datasets` `page-state` | `dataset` `dataset_commit` `job` |
| ④ 模型训练 | `功能点/04-模型训练.md` | 模型训练 `/train` | `train` `datasets` `page-state` | `dataset` `dataset_commit` `model` `model_artifact` `job` |
| ⑤ 模型预测 | `功能点/05-模型预测.md` | 模型预测 `/predict`；详情 `/predict/{job_id}/commit/{commit_hash}` | `predict` `datasets` `page-state` | `dataset` `prediction` `model` `model_artifact` `job` |
| ⑥ 预测性能评估 | `功能点/06-预测性能评估.md` | 模型评估 `/evaluate` | `evaluate` `page-state` | `evaluation` `evaluation_figure` `prediction` `dataset` `model` `job` |
| ⑦ 预测结果解释 | `功能点/05-模型预测.md` 第 5 节 | 预测详情 `/predict/{job_id}/commit/{commit_hash}` | `predict` | `prediction` `dataset` `model` `model_artifact` |
| ⑧ 缺陷定位及修复 | `功能点/05-模型预测.md` 第 6 节 | 预测详情 `/predict/{job_id}/commit/{commit_hash}` | `predict` | `prediction` `dataset` |

- 页面或接口调整时同步改本表；本表是「功能点—页面—接口—表」的唯一对应关系。
- 表格中的接口名对应 `接口/<name>.md`；表名对应 `数据库/<name>.md`，未单独成稿的表以 `infra/schema.sql` 为准。
- 登录不属于设计图 9 项，编号为 00，避免打乱 ①–⑧。

## 5 编写规则

1. 只描述最新设计，不写阶段划分、历史版本、已废弃或已移除的能力。
2. 不写不存在的能力；范围外内容只在功能点或对应包的「边界」小节声明一次。
3. 数量类口径（功能点数、页面数、表数、算法数）只在真源处写，其它文档引用不复写。
4. 每篇文档的验收条件必须可观察：能通过页面操作、接口响应或命令输出判定通过与否。
5. 文档中的文件路径与路由必须可点击或可校验，不留失效引用。

## 6 设计原则与硬约束

实现时以下条目优先于任何旧代码、README 片段或 `openspec/` 内容：

1. **保存边界**：数据集、模型、预测结果、评估历史只在用户主动点击「保存到数据库」时写入；执行、预览、导出、刷新、重新登录都不入库。页面进度只写 `user_page_state`。
2. **输入校验**：所有外部 CSV / Excel 逐列校验列名、顺序与数量；缺列、多列、列序不符直接拒绝，不能进入下一步。唯一例外是预测输入允许缺 `bug`。
3. **用户隔离**：所有业务数据按当前会话用户处理，不接受前端传 `user_id`；非本人资源一律返回 `40401`。
4. **受控冗余**：不追求严格 BCNF，允许 `dataset_commit` 快照、`evaluation` / `prediction` 展示字段；冗余只读，不作为新的写入真源。
5. **提交标识**：`commit_id` 是内部主键，`commit_hash` 是 Git 内容哈希；同一哈希在不同仓库分行，历史特征按仓库计算。JSON 接口一律用 `commit_hash`，外部导入/导出表头用 `commit_id`。
6. **模型格式**：sklearn 算法存 `.pkl`，dnn / tabnet 存单文件 `.pt`；下载扩展名必须跟随 `model_artifact.format`。
7. **会话**：会话存 `user_session`，Cookie 只放原始令牌；登出删行后旧 Cookie 立即失效。
8. **临时文件**：上传与任务产物只落 `temp/`；页面重置、开始新流程或校验失败时清理，已保存资产复制到 `temp/datasets/` / `temp/models/` / `temp/evaluations/`。
9. **任务**：同一用户同一时刻只允许 1 个运行中任务；状态、取消与重试以 `约束/job-state.md` 为准。
10. **口令**：课程演示项目按明文存储与比对，禁止用于生产环境；接口不回传口令字段。
11. **真源优先级**：设计口径以 `docs/` 为准；`openspec/` 是历史归档，不得作为实现依据。

## 7 历史归档

- `openspec/` 与仓库内旧版 README / 部署说明只用于追溯历史，不作为实现或验收依据。
- 实现与本文冲突时，以 `docs/` 与 `infra/schema.sql` 为准。
