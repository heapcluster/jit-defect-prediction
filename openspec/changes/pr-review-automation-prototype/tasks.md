# pr-review-automation-prototype — 任务清单

> 提案：`proposal.md` ｜ 设计决策：`design.md` ｜ 规格：`specs/pr-review-automation/spec.md`
> 负责人：repo 苏哲勋｜ 创建：2026-10-23 ｜ 状态：进行中
> 用户故事：无（工程化）
> 统一格式见 `docs/common/openspec-task-template.md`；本文件末的「测试与验证」为强制板块，缺失视为提案不完整。

## 1. 原型实现（工程化）

- [x] 1.1 实现只读 PR 触发工作流 — `.github/workflows/pr-auto-review-prototype.yml`；核对权限仅为 read、无 PR 头 checkout。
- [x] 1.2 实现差异完整性、SHA、CI 与证据校验 — `infra/pr_auto_review.py`；运行 `python -m unittest discover -s infra/tests -v` 为 8 passed。
- [x] 1.3 落地默认不发布配置与使用说明 — `infra/pr_review_config.json`、`infra/README.md`；配置为 `provider=none`、`publish=false`。
- [ ] 1.4 在线验证 Actions 在 PR 更新时只读执行 — GitHub Actions 运行链接与日志；工作流先合入默认分支，再由后续 PR 更新触发并补证据。

## 测试与验证（强制板块）

### 1. 单元测试

| 项 | 内容 |
|---|---|
| 覆盖对象 | `choose_action`、`inspect_files`、默认只读运行 |
| 测试文件 | `infra/tests/test_pr_auto_review.py` |
| 用例数与结果 | 8 条，8 passed（本地 2026-10-23） |
| 复现命令 | `python -m unittest discover -s infra/tests -v` |
| 正向用例 | 当前 SHA、完整补丁、CI success、空 findings → 提议 APPROVE |
| 异常 / 边界用例 | 过期 SHA、缺失/截断补丁、失败 CI、无补丁证据 → SKIP |

### 2. 集成测试

| 项 | 内容 |
|---|---|
| 集成范围 | PR 事件 → GitHub 文件列表 → 本地策略；不接模型与发布 |
| 测试文件 | `infra/tests/test_pr_auto_review.py` |
| 用例数与结果 | 1 条模拟 API 测试通过；真实 Actions 未运行 |
| 复现命令 | `python -m unittest discover -s infra/tests -v` |
| 关键断言 | 无决策时仅执行 GET，不提交审阅 |

### 3. 验收测试

| 项 | 内容 |
|---|---|
| 验收依据 | `specs/pr-review-automation/spec.md` 的 4 个 Scenario |
| 用例数与结果 | 离线 4 类已覆盖；线上触发与权限待验证 |
| 复现命令 / 步骤 | `python -m unittest discover -s infra/tests -v`；工作流合入默认分支后更新后续 PR，检查 Actions 日志与审阅列表 |
| 证据归档 | `infra/tests/test_pr_auto_review.py`；线上运行链接待补 |

### 4. 非功能验证

| 维度 | 是否触及 | 证据 |
|---|---|---|
| 性能 | 是 | 补丁默认上限 200000 字节、80 文件；`infra/pr_review_config.json` |
| 安全 | 是 | 只读权限、无 PR 头代码执行、无凭据；`.github/workflows/pr-auto-review-prototype.yml` 与离线边界测试 |
| 可靠 | 是 | 过期 SHA、重复审阅与补丁不完整时失败关闭；`infra/pr_auto_review.py` |
| 易用 | 否 | 本 change 不触及前端交互 |

### 5. 已知缺口与后续计划

| 缺口 | 原因 | 归属 | 计划时间 |
|---|---|---|---|
| 线上 Actions 首次运行与真实权限验证 | 工作流须先合入默认分支；当前分支尚未推送，本机 GitHub 命令行凭据失效 | repo 苏哲勋 | 原型 PR 合入后下一次 PR 更新 |
| 模型 API、代码差异外发审批、自动发布审阅 | 用户要求先做可配置原型，暂不启用 API；服务商与凭据未定 | repo 苏哲勋 | 后续独立 change |
| OpenSpec CLI 形式校验 | 本机 `openspec` 命令不可用，尚未执行 CLI validate | repo 苏哲勋 | 工具就绪后、合入前 |
