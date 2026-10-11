# 后端 OpenSpec 合规（每次改动必须走规范）

> 适用：吕建江及所有改 `backend/` 的人 ｜ 关联：`docs/common/openspec-rules.md`

## 🔴 铁律

**改后端行为 = 先提 OpenSpec change，后写代码。只改代码不更新规格 = 课程判定为缺陷。**

## 1. 什么时候必须提 change

| 改动 | 走什么 |
|---|---|
| 接口加字段 / 改响应结构 | 契约三变更 change（proposal → 评审 → apply → archive） |
| 新增接口 | 新 change（如 `predict-api` 即此类） |
| 错误码 / 鉴权口径变更 | 契约三变更 |
| 库表加列 | 契约一（`data-fields.md`）变更 + 对应 change |
| 纯修复 Bug（不改规格语义） | 开 `type:bug` Issue + PR，但仍须同步任何受影响的 spec |

## 2. 字段一致铁律（最易踩）

- 接口返回的 `features` 14 项键名，必须与 `docs/model/README.md` 指向的 `feature-columns.md` **逐字一致**。
- 库表字段名与 `docs/design/database.md`（契约一）逐字一致。
- **前端、后端、模型线三处字段名必须同一份来源，禁止各写一份。**

## 3. 标准工作流（SDD）

```
propose（写码前） → 规范评审（苏哲勋，提案人≠审阅人） → apply（按 tasks.md 勾选+验证）
→ PR（描述写 change id，苏哲勋非作者审阅） → archive（合入后 openspec archive，规格并入 specs/）
```

- 顺序错了（码写完了再补提案）= 没走 SDD。
- `tasks.md` 勾了 ≠ 功能合格，必须有运行/验收测试证据。

## 4. 后端相关 change 清单（当前）

| change | 状态 | 说明 |
|---|---|---|
| `predict-api` | 已实现待归档 | `POST /api/predict` 实时推理 |
| `nfr-evidence-scripts` | 部分未勾 | 性能/安全证据脚本（tasks 4.1/4.3/4.4 待清零） |
| 契约三变更 | 走 `docs/common/openspec-rules.md` | 接口格式冻结后改动 |

> 未归档 change 在 Sprint 末必须清零（见 `docs/repo/openspec-workflow.md` §节奏）。
