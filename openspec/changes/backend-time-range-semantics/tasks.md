## 1. 后端实现与测试

- [x] 1.1 `_parse_time` 增加 role 参数：end 侧纯日期串按当天 23:59:59.999999 收尾，start 侧保持 00:00:00；commits 与 trends 两调用点同步
      —— 完成：`backend/app/api/commits.py`（定义 + 调用点）、`backend/app/api/trends.py`（调用点）
- [x] 1.2 回归测试 4 条：列表 end 纯日期含全天、end 带时间分量不变、start 纯日期仍午夜、趋势 end 纯日期含全天
      —— 完成：`tests/test_commits_api.py` 3 条 + `tests/test_trends_api.py` 1 条；pytest 40/40、ruff check/format 清

## 2. 契约与引用同步

- [x] 2.1 契约三升 2.0：§3 两处参数表 + 区间语义注 + 变更日志行（口径补充，1.0 步进）
      —— 完成：`docs/contracts/api-format.md`
- [x] 2.2 全仓引用点 1.4 → 2.0：backend 7 处 docstring、`openspec/specs/query-api/spec.md` 3 处、`docs/contracts/README.md` 状态表/说明行/变更日志 1.6
      —— 完成：grep 复扫零残留（历史陈述不动）

## 3. 跨线待办（不在本 PR）

- [ ] 3.1 前端月粒度 `periodToRange` 的 end 改送当月最后一日（新语义下「次月 1 日」会多收结束日全天）—— 刘帅华，PR #60 内跟进
- [ ] 3.2 合入后归档本 change（delta 落 `openspec/specs/query-api`）
