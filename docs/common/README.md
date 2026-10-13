# common 包（公共规范）· 全员

> **本文件夹是所有人开工前先读的公共入口。** 读完 common，再打开你自己的包 README，你就能清楚：自己负责什么、最近要干什么、每次任务怎么干。
> 统稿：蒋励 ｜ 审核：苏哲勋

---

## 🚦 新成员上手 3 步（先看这里）

**第 1 步｜读 common（本文件夹）的 3 份：**
- `course-requirements.md` — 课程《项目要求》原文 + 本项目逐条映射（你要交付的东西对应哪些分数）
- `openspec-rules.md` — **每次改动必须走规范**（SDD 铁律：改需求先提 change，只改码不改规格=缺陷）
- `team-charter.md` — 四人分工、审阅人、时间约定

**第 2 步｜打开你自己的包 README（按名字对号入座）：**

| 你是谁 | 打开哪个文件夹 | 你负责什么（一句话） |
|---|---|---|
| 吕建江 | `docs/backend/README.md` | 后端接口 + 在线预测 + 性能/安全证据 |
| 刘帅华 | `docs/frontend/README.md` | 三页面 + ECharts 可视化 + 联调 |
| 蒋励 | `docs/model/README.md` | 数据采集/SZZ/14特征/8模型/两类指标/SHAP + SM 统稿 |
| 苏哲勋 | `docs/repo/README.md` | 工程基线/PR审阅/看板/周报/OpenSpec 推进 + PO |
| 任何人（设计供稿） | `docs/design/README.md` | 往设计基线补自己线的那几节 |

每个包 README 里都有：**👤 你的职责一句话 → 📋 你的任务清单（带验收+状态）→ 🚀 标准动作 → 🚫 红线 → 子文件导航**。

**第 3 步｜按"标准动作"开工：** 认领（飞书看板）→ 判断要不要动规格 → 要动就提 OpenSpec change → 实现并同步规格 → 自测 → 提 PR（非作者审阅）→ 合入 → 归档 + 回写看板/周报。

---

## 权威边界（务必先读）

**任务在飞书、代码在仓库。** 需求范围/背景/功能说明在飞书《产品需求文档》《产品设计文档》；代码边界/契约/映射/手册在仓库 `docs/`。
任何结论必须落到文档或 Issue，只在聊天里说过的决定 = 没定。

> 飞书源文档：产品需求文档 `PgG0dvODooN1clxgV65ctC6JnQg`；项目要求 `SG8rdplK4oZA7mxBKM0cqBFrnTd`；设计文档见飞书《产品设计文档》（`docs/design/prototype.md` 指针）。

## 本包管什么

跨线公共的规范与依据，任何人可改但同样走 PR：
- 课程要求原文与本项目映射
- OpenSpec 规则（**每次改动必须走规范**）
- 文档写作规范、团队章程、开工手册
- 术语表、模板基线
- **测试方案总纲**（`test-plan.md`：四层测试 + 用例清单 + 退出准则）

## 谁依赖这个包

本包是**所有人的第一站**——每个包 README 的「先读 common 里的哪几份」都指回这里。

| 依赖方 | 依赖什么 | 卡住的后果 |
|---|---|---|
| 全员 | `course-requirements.md`（课程要求 → 分数映射） | 不知道交付物对应哪些分，做偏方向 |
| 全员 | `openspec-rules.md` + `test-plan.md` | 改动不走 change = SDD 缺陷；测试无总纲 = 测试实践缺项 |
| 蒋励（SM） | `team-charter.md`（分工/审阅人）、`acceptance-overview.md`（跨包验收 + 一票否决） | 周报对账与验收判定无统一口径 |
| 各线 | `templates.md`（周报/PR/Issue 模板基线） | 模板被各自改动 → 周报过程证据失分 |
| 新成员 | `dev-handbook.md`（分线开工步骤） | 上手慢，重复踩已记录的坑 |

> 本包**不依赖**业务包的产出（只依赖课程《项目要求》与团队约定），因此可与业务开发并行维护。

## 子文件导航

- `course-requirements.md` — 课程《项目要求》原文 + 本项目逐条映射
- `openspec-rules.md` — OpenSpec SDD 规则（变更触发、字段一致、生命周期）
- `writing-norms.md` — 文档命名/注释/排版/周报规范（合并自 `docs/writing-norms.md`）
- `team-charter.md` — 分工/协作/时间（合并自 `docs/team-charter.md`）
- `dev-handbook.md` — 代码项目开工手册（合并自 `docs/dev-handbook.md`）
- `glossary.md` — 术语表
- `templates.md` — 周报/PR/Issue 模板基线（原 `docs/templates/`）
- `test-plan.md` — **测试方案总纲**（四层测试 / 用例清单 / 测试环境前置 / 退出准则）

## 各包总导航（快速跳转）

- `../backend/` 吕建江 ｜ `../frontend/` 刘帅华 ｜ `../model/` 蒋励 ｜ `../repo/` 苏哲勋 ｜ `../design/` 全员
- 文档地图总入口：`../README.md`（含 §0 组长 docs PR 强制合入规则）
