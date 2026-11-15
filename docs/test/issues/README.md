# 缺陷 Issue 草稿与维护记录

> 本目录是**测试方提交 issue 的工作底稿**：新单可直接粘贴到 GitHub，更新/合并草稿可直接作为评论发出。
> 处理规则见 [`../defect-handling.md`](../defect-handling.md)：测试方只提不修，修复归模块 owner。

## 1 · 清单

### 待提交的新单（正文见 `new/`）

| 本地编号 | 标题 | 建议级别 | 建议 label | 状态 |
|---|---|---|---|---|
| BUG-01 | 干净检出缺 `backend/static/` 目录，`app.main` 导入即失败 | 严重 | `type:bug` `line:backend` | **已提交 #239** |
| BUG-02 | `/api/figures` 返回的 6 个图路径无实体文件，`/static/figures/**` 带令牌仍 404 | 严重 | `type:bug` `line:backend` `line:model` | **已提交 #240** |
| BUG-03 | 并发触发同步时第二个请求返回 500 `internal error` | 一般 | `type:bug` `line:backend` | **已提交 #241** |
| BUG-05 | `README.md` 称 `GET /api/health` 公开，实际要求 `X-API-Key` | 轻微 | `type:docs` `line:docs` | **已提交 #242** |

另两条不单独开单：

- **BUG-04**（tabnet 权重加载失败被包装成「参数非法 40001」）与 #222 同源，作为评论并入 #222，见 [`issue-maintenance.md`](issue-maintenance.md) §2.1。
- **BUG-06**（`system_exceptions.py` 空库场景依赖测试库恰好为空）属测试脚本自身缺陷，已在脚本内修复并回归（13/13），不开产品 issue，仅在 [`../system_test/bug_list.md`](../system_test/bug_list.md) 留痕。

### 待更新 / 待合并的历史单

见 [`issue-maintenance.md`](issue-maintenance.md)：6 条待更新（#225 / #226 / #227 / #229 / #230 / #233）、3 组已完成的重复合并（#218→#217、#217+#218→#226、#220→#228）。

## 2 · 提交方式与执行记录

2026-11-15 已用仓库贡献者身份（`jolly326`，Git Credential Manager 中的 HTTPS 凭据）通过 GitHub REST API 完成提交，未安装 `gh` CLI。执行结果：

| 动作 | 结果 |
|---|---|
| 新建 4 条缺陷 | #239（BUG-01）、#240（BUG-02）、#241（BUG-03）、#242（BUG-05），labels 均按上表挂好 |
| 更新 8 条历史单 | #222、#225、#226（含合并记录）、#227、#228（含承接声明）、#229、#230、#233 各追加评论 |
| 补充说明 4 条已关闭单 | #217、#218（并入 #226）、#219（关闭但未修）、#220（剩余项归 #228） |
| 修正标题 | #229「五个能力目录」→「四个能力目录」 |

后续新缺陷沿用同一流程，脚本化方式（令牌从 git 凭据读取，不写盘）：

```bash
TOKEN=$(printf 'protocol=https\nhost=github.com\n\n' | git credential fill | sed -n 's/^password=//p')
curl -s -X POST https://api.github.com/repos/heapcluster/jit-defect-prediction/issues \
  -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.github+json" \
  -d '{"title":"...","body":"...","labels":["type:bug","line:backend"]}'
```

更新已有单时只发评论或编辑正文，**不关闭他人未修的 issue**（重复合并除外，且需保留单 owner 确认）。

## 3 · 检查项

提交前逐条确认（缺一项就别发）：

- [ ] 五要素齐全：现象 / 复现步骤 / 预期结果 / 实际结果 / 影响范围
- [ ] 复现步骤带前置条件（SHA、环境、数据前提），命令可复制
- [ ] 实际结果贴了响应体 / 日志 / 截图文件名，不是"报错了"
- [ ] 写了影响范围（哪些端点、页面、模型、环境；是否阻断验收）
- [ ] 有建议级别与归属模块
- [ ] 无密钥、令牌、个人数据、真实用户信息
