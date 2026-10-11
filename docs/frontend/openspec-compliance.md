# 前端 OpenSpec 合规

> 适用：刘帅华及所有改 `frontend/` 的人 ｜ 关联：`docs/common/openspec-rules.md`

## 🔴 铁律

**页面要新字段 = 先改契约 / 提 change，不要前端自己造字段。**

## 1. 什么时候提 change

| 改动 | 走什么 |
|---|---|
| 页面要接口没返回的字段 | 先改 `docs/backend/api-spec.md`（契约三变更）或提 change，前端再接 |
| 新增页面交互需要新接口 | 新 change（如需要 `GET /api/models` 动态模型清单） |
| 三态/阈值口径变更 | 改 `frontend/pages.md` 并同步契约 |
| 纯视觉/布局调整 | 可不走 change，但 PR 仍须审阅 |

## 2. 字段一致铁律

- 页面变量名 = 接口返回字段名（不驼峰转换）。
- `features` 键名必须与 `feature-columns.md` 一致（否则解释条静默空白）。

## 3. 标准工作流

propose(`frontend-integration`) → 规范评审（苏哲勋） → apply（按 tasks 勾选+联调证据） → PR（写 change id，苏哲勋审） → archive。

> 当前 `frontend-integration` change 待 F2/F3/F4 推进；Sprint 末归档清零。
