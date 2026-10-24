# 分支与 PR 规范速查

> 来源：原 `docs/collaboration.md` §1–§3（已并入 repo/collaboration.md） ｜ 负责人：苏哲勋

## 分支命名

```
feat/model/szz-labeling
fix/backend/predict-api
docs/backend/api-spec
```
类型 `feat/fix/docs/refactor/test/chore`；线 `model/backend/frontend/infra/docs/spec`。PR 合入后立即删。

## 日常六步

```bash
git checkout main && git pull
git checkout -b feat/backend/predict-api
git add backend/app/api/predict.py      # 加具体文件，不 git add .
git commit -m "feat(backend): 新增预测接口"
git push -u origin feat/backend/predict-api
# 网页开 PR（描述四件事）→ 苏哲勋审阅 → Squash 合入 → 删分支
git checkout main && git pull && git branch -d feat/backend/predict-api
```

## 禁止

- 直推 main；`git push --force`（除未推且没开 PR）；删别人分支；未完成的改动切分支接着干。
- 自己合自己未审阅的 PR；PR 夹数据集/模型/`.env`/密钥；夹带顺手重构。

## PR 描述四件事

1. 改了什么 2. 为什么改（对应 change）3. 怎么验证 4. 关联编号。

## 审阅人

- 吕建江/刘帅华/蒋励 → 苏哲勋；苏哲勋 → 蒋励。
- **文档线**：组长蒋励（账号 `jolly326`）的 `docs/` PR，除 `repo/collaboration.md` §3.8 的六种必须 Request changes 情形外直接 Approve；**§3.8 优先，不是无条件合入**。

## 冲突

只在自己分支解；解完跑该线自检；不确定问对方；解完照常 push（PR 自动更新）。用 `merge` 不用 `rebase --force`。
