## 1. 后端实现与测试

- [x] 1.1 `_parse_time` 增加 role 参数：end 侧纯日期串按当天 `23:59:59.999999` 收尾，start 侧保持 `00:00:00`；紧凑基本格式（头 8 位数字后接 T 或结束，含 Z/偏移变体）拒收 40001；commits 与 trends 两调用点同步
      —— 完成判据：代码合入且 6 条回归测试绿。完成：`backend/app/api/commits.py`（定义+调用点）、`backend/app/api/trends.py`（调用点），提交 2b366ac
- [x] 1.2 回归测试 6 条：列表 end 纯日期含全天、end 带时间分量不变、start 纯日期仍午夜、趋势 end 纯日期含全天、列表/趋势紧凑基本格式（含 `20260803T090000Z`、`+08:00` 变体）拒收 40001
      —— 完成判据：`pytest tests/ -q` 全绿且新用例覆盖上述输入。完成：`tests/test_commits_api.py` 4 条 + `tests/test_trends_api.py` 2 条，45/45（2b366ac）

## 2. 契约与引用同步

- [x] 2.1 `docs/backend/api-spec.md` 升 1.5：§一 新增「时间范围语义」表行（闭区间 + 纯日期串解释 + 紧凑格式拒收 + 前端 MUST NOT 调用侧补丁及理由）、文件头版本、变更日志节（1.5 前历史指向旧 `docs/contracts/api-format.md` git 历史）
      —— 完成判据：契约行可判定、变更日志含「改了什么/为什么」。完成：2b366ac
- [x] 2.2 全仓引用点 1.4 → 1.5 与路径重定向：backend docstring 7 处、`backend/README.md` 的 `docs/contracts/*` 路径 4 处（12:41 归属裁定：后端线仅此一文件）
      —— 完成判据：`grep -rn "docs/contracts" backend/` 零残留、docstring 版本一致。完成：2b366ac

## 3. 跨线待办（不在本 PR）

- [ ] 3.1 前端月粒度 `periodToRange` 的 end 改送当月最后一日；toEndTime 兜底与 `docs/frontend/pages.md` 过渡句在 #62 合入后移除 —— 刘帅华，PR #60（10-12 协调意见已留）
- [ ] 3.2 合入后归档本 change（delta 落 `openspec/specs/query-api`，含 1.4→1.5 版本引用同步）—— 吕建江，归档 PR

## 4. 测试与验证

### 4.1 场景覆盖矩阵

| 场景 | 输入 | 预期 | 覆盖位置 | 结果 |
|---|---|---|---|---|
| end 纯日期含全天 | `start=2026-08-03&end=2026-08-03` | 含当天 09:00 提交，total=1 | `test_commits_api.py::test_end_pure_date_includes_whole_end_day` | PASS |
| end 带时间分量不变 | `end=2026-08-03T08:59:59` / `T09:00:00` | 前者不含 09:00 提交、后者含 | `test_end_with_time_component_unchanged` | PASS |
| start 纯日期仍午夜 | `start=2026-08-03` | 含当天全部提交 | `test_start_pure_date_still_midnight` | PASS |
| 趋势 end 纯日期含全天 | 同上，`/api/trends` | 周桶 2026-W32 计数 1 | `test_trends_api.py::test_end_pure_date_includes_whole_end_day` | PASS |
| 紧凑格式拒收 | `20260803` / `20260803T090000Z` / `20260803T090000+08:00` | 400 + 40001，message 指参数名 | 列表/趋势各一条 | PASS |
| 时间范围内无数据 | 2030 年区间 | code=0、空结果（既有语义不回归） | 既有 `test_empty_range_is_not_error` | PASS |

### 4.2 验证清单

- [x] 单元测试：`pytest tests/ -q` → 45 passed（含新增 6 条）
- [x] 静态检查：`ruff check app/ tests/` → All checks passed
- [x] 规格校验：`openspec validate --all --strict` → 本 change 通过（main 既有 `frontend-integration` 空 delta 失败非本 change 引入，已留言 #62）
- [x] 契约一致性：api-spec 1.5 表行与 `_parse_time` 行为逐条对读（闭区间/纯日期/紧凑拒收/MUST NOT）
- [ ] 集成测试：与前端 #60 联调时验证周下钻 `commit_count` 与列表条数一致（F4 联调记录，#62 合入后执行）
- [ ] 验收测试：10/23 端到端演示脚本含「时间范围筛选」正向+异常用例（蒋励 `docs/weekly/demo-script-sprint1.md` 收口）

### 4.3 执行证据

- 提交：2b366ac（分支 fix/backend/time-range-closed，PR #62）
- 环境：Windows 11 / Python 3.12.7 / 仓库 `.venv`（fastapi 0.141.1、sqlalchemy 2.0.54、pytest 9.1.1）
- 命令与结果：`pytest tests/ -q` → `45 passed, 2 warnings in 2.97s`；`ruff check app/ tests/` → `All checks passed`；`openspec validate --all --strict` → `12 passed, 1 failed`（失败项 frontend-integration，main 既有）
- 链接：PR #62（含 10-11 三轮复审与回复）、Issue #61

### 4.4 阻断 / 不适用说明

- 集成/验收两项未执行：前置为 #62 合入与 F4 联调排期，非本 change 可控；不写成已完成。
- 46 处历史路径引用（AGENTS.md、data_model 等）按 10-11 12:41 裁定不归本 change（苏哲勋/蒋励分工）。

### 4.5 落地结论

- 代码与契约同改、同 PR 落地；区间语义自 1.5 起可判定；结束日丢数据与紧凑格式二义性在单测层闭环，集成/验收层挂 F4 与 10/23 演示两个明确下游。
