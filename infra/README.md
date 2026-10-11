# infra/ — 工程化与协作线

> 版本 1.1 ｜ 更新 2026-10-06 ｜ 主笔 苏哲勋 ｜ 审核 蒋励

**负责人**：苏哲勋

## 职责

GitHub 仓库配置、分支规范与分支保护、PR / Issue 模板、CI 流水线、缺陷管理。

## 交付物

仓库规范、CI 配置、PR / Issue 模板。

> **三条契约的归属已裁定**（飞书《讨论0915-项目启动与分工》）：落点在 `docs/contracts/`，契约一（数据表字段）与契约二（特征列名）由蒋励主笔，契约三（接口格式）由吕建江主笔。本线只负责「契约怎么冻结、怎么走变更」的**规则**，不另写一份契约。本目录只放工具与配置。

## 边界

- `main` 分支受保护，禁止直接推送；合并前至少 1 位非作者审阅。
- CI 等有可测代码之后再接（`openspec validate` 也一并进流水线）。
- 只在本目录内写代码。

## 仓库设置清单（网页端操作，文件落地不了）

`main` 的分支保护、标签、协作者只能在 GitHub 网页端设置，**没有文件能替代**。第一次协作提交前逐项确认：

| 项 | 设置成 | 为什么 |
|---|---|---|
| 默认分支 | `main` | — |
| `main` 分支保护 | 禁止直接推送、禁止强制推送、合并前至少 1 位审阅 | 课程明确要求 |
| Squash merge | 设为唯一允许的合并方式 | `docs/collaboration.md` 第 3.4 节：`main` 历史保持线性 |
| Automatically delete head branches | 开启 | 分支不堆积 |
| 标签 | 按 `docs/collaboration.md` 第 5 节建全：`type:feat` `type:bug` `type:docs` `type:test`、`line:model` `line:backend` `line:frontend` `line:infra` `line:docs`、`sprint:0` `sprint:1` … | **`.github/ISSUE_TEMPLATE/` 里的标签引用需要标签已存在才生效**，缺了不报错、只是静默不挂上 |
| 协作者 | 三位组员加入，给写权限 | 否则无法推分支 |
| 可见性 | 私有（结题前视课程要求决定是否转公开） | 与根 `README.md` 第二节一致 |

模板文件已就位：`.github/pull_request_template.md`、`.github/ISSUE_TEMPLATE/task.md`、`.github/ISSUE_TEMPLATE/bug.md` —— 建 PR / Issue 时自动带出，无需额外操作。

## 自检：怎么确认这些设置真的生效

**为什么单列一节**：`main` 的分支保护是**服务端设置**，仓库里没有任何文件能反映它 —— 网页上勾没勾，`clone` 下来看不出来。0911 周报里记的「设置读不到（API 404 / 权限不足）」是**误诊**，下面会说清症结在哪。这一节的命令**任何人照做就能自查**，不需要管理员权限。

前置：装好 `gh`，`gh auth login` 后对本仓库有读权限即可。

```bash
R=heapcluster/jit-defect-prediction
```

### 1. 仓库级设置（一条命令看全貌）

```bash
gh api repos/$R --jq '{default_branch,allow_squash_merge,allow_merge_commit,allow_rebase_merge,delete_branch_on_merge,visibility}'
```

期望输出（2026-10-06 实测；`--jq` 的**键序不保证**，逐项核对即可）：

```json
{"allow_merge_commit":false,"allow_rebase_merge":false,"allow_squash_merge":true,"default_branch":"main","delete_branch_on_merge":true,"visibility":"public"}
```

逐项对上清单：默认分支 `main` ✓ ｜ Squash merge 唯一（`merge` 与 `rebase` 均为 `false`）✓ ｜ 自动删分支 ✓。

### 2. 分支保护：读 ruleset，**不要**读经典端点

```bash
gh api repos/$R/branches/main --jq .protected          # 期望 true
gh api repos/$R/rulesets --jq '.[] | {id,name,enforcement}'
gh api repos/$R/rulesets/<id> \
  --jq '{enforcement,bypass_actors,rules:[.rules[]|{type,parameters}]}'
```

`<id>` 取第二条输出里的 `id`（2026-10-06 为 `23522853`）。期望看到 `enforcement: "active"`、`bypass_actors: []`（**没有豁免名单，管理员也绕不过**），以及三条规则：

| ruleset 规则 | 对应清单里的哪一条 |
|---|---|
| `deletion` | （额外）禁止删除 `main` |
| `non_fast_forward` | 禁止强制推送 |
| `pull_request` → `required_approving_review_count: 1` | 禁止直接推送（改动必须走 PR）+ 合并前至少 1 位非作者审阅 |

> **注意 `allowed_merge_methods` 这一项别误读。** ruleset 的 `pull_request.parameters.allowed_merge_methods` 列出的是 `["merge","squash","rebase"]` 三种，**比清单里的「Squash 唯一」宽松** —— 真正把合并方式收成 Squash 的是**仓库级设置**（第 1 步里的 `allow_merge_commit: false` / `allow_rebase_merge: false`），两者叠加后的**实际行为是 Squash 唯一**。**只读 ruleset 会得出「三种都能合」的反结论** —— 所以第 1 步和第 2 步要一起看。

> **❗ 别用 `gh api repos/$R/branches/main/protection`。** 本仓库的保护是用 **ruleset** 配的，不是经典的 branch protection；那个端点恒返回
> `404 {"message":"Branch not protected"}` —— 看着像「没设保护」或「没权限」，其实两者都不是。0911 周报里「API 404 / 权限不足」的结论就是这么来的：**查错了端点**。

### 3. ⚠️ `git push --dry-run` 不能用来验证拦截

**实测结论：`--dry-run` 不会触发服务端的规则检查，给的是假阳性。**

在 `main` 上造一个临时提交后跑：

```bash
git push --dry-run origin HEAD:main
# To https://github.com/heapcluster/jit-defect-prediction.git
#    e05f8be..3324a7a  HEAD -> main        ← 看着「能推」，退出码 0
```

真推会被拒（GH006），但 `--dry-run` 照样打印成一条正常推送。**所以不要拿它当分支保护的自检证据。**

配置即事实：第 2 步读出 `enforcement: active` + `bypass_actors: []`，说明这份 ruleset 就是服务端正在强制执行的那份，**不需要再靠一次真实推送去"试"**。真要做行为验证，只在你本来就要往 `main` 推东西时顺带观察 —— 不要为验证专门造提交。

### 4. 标签

```bash
gh api "repos/$R/labels?per_page=100" --jq '.[].name' | sort
```

期望输出 = `docs/collaboration.md` 第 5.1 节那三组，共 **12** 个：

```
line:backend line:docs line:frontend line:infra line:model
sprint:0 sprint:1
type:bug type:chore type:docs type:feat type:test
```

**`type:` / `line:` / `sprint:` 三组缺任何一个都不会报错** —— `.github/ISSUE_TEMPLATE/` 里的标签引用只是**静默不挂上**。所以要靠这条命令核，不能靠「建个 Issue 看看有没有标签」。

> 2026-10-06 实测多出一个 `bug`（不在上述 12 个内），来源待查，去留由 infra 线裁定。

### 5. 模板与协作者

```bash
git ls-files .github/                                   # 期望三份模板
gh api repos/$R/collaborators --jq '.[].login' | sort
```

协作者期望四人：`1lsh74269` `jolly326` `s1mple-less` `sober-hub`。

### 6. ruleset 里写了、但上面的清单没提的两条行为

- **`dismiss_stale_reviews_on_push: true`** —— PR 上有人推新提交后，**已有的 Approve 会被作废**，需要重新审。方向是对的（审的应是新版本），但**改完必须回 PR 里 @ 审阅人**，否则那条 PR 会一直挂在「等审阅」上没人知道。
- **`require_extra_approval_for_unattributed_changes: true`** —— PR 里若有**提交作者未关联到 GitHub 账号**的提交，需要**额外一位 Approve**。本仓库已知有一例：刘帅华（`1lsh74269`）本地没配 `user.name`，提交署名是 `unknown <486431190@qq.com>`。**如果某条 PR 明明已有 1 个 Approve 却合不了，先查这一条。**

## 文档落点（别写重了）

| 内容 | 落点 |
|---|---|
| 分支 / 提交 / PR / Issue 的**说明**（人读的） | `docs/collaboration.md` |
| PR 模板、Issue 模板、分支保护配置（**机器读的**） | `.github/` 与本目录 |
| 三条契约 | `docs/contracts/` |
| 技术规格与变更提案 | `openspec/` |

**说明放 docs，模板放 .github** —— 两边不重复写同一段规则，本目录只留指针。

## 团队工具版本约定

**OpenSpec CLI：全员统一 1.11.0。**

```bash
npm install -g @fission-ai/openspec@1.11.0   # 带死版本号，不要用 @latest
openspec --version                            # 应输出 1.11.0
```

- 前置：Node.js ≥ 20.19.0。
- **不要各人跑完 `openspec update` 就直接提交生成文件。** `update` 按*本机 CLI 版本*重新生成斜杠命令文件，版本不一致会把别人的新命令覆盖回旧版。升级版本先在群里说一声，全员一起升。
- `.codebuddy/`、`.claude/`、`.qoder/`（AI 工具集成文件）**必须提交**，不要写进 `.gitignore`。

### 三种工具并存，互不冲突

| 工具 | `--tools` id | 生成目录 | 斜杠命令拼法 |
|---|---|---|---|
| CodeBuddy | `codebuddy` | `.codebuddy/` | `/opsx:propose` |
| Claude Code | `claude` | `.claude/` | `/opsx:propose` |
| Qoder | `qoder` | `.qoder/` | `/opsx:propose` |

**三款完全等价，表中顺序无含义** —— 你机器上装的是哪款就用哪款，不要因为某一款排在前面就当它是默认选项。路径按工具名分开，三套文件同时存在不会相互覆盖；三款工具的斜杠命令拼法完全一致。

### 一次性初始化（由组长在仓库根目录执行）

**⚠️ PowerShell 里逗号是数组分隔符**：直接写 `--tools codebuddy,claude,qoder` 会被 PowerShell 拼成一个带空格的参数传给 CLI，报错 `Invalid tool(s): codebuddy claude qoder`（三个 id 都"无效"，看起来像 id 写错了，实际是引号问题）。**必须加引号**：

```powershell
# PowerShell（本机默认）—— 引号不可省
cd D:\workspace\code\course\jit-defect-prediction
openspec init --tools "codebuddy,claude,qoder"
```

```bash
# bash / Git Bash 无此问题
openspec init --tools codebuddy,claude,qoder
```

**验收标准**：终端出现 `Created: CodeBuddy Code (CLI), Claude Code, Qoder` 与 `7 skills and 7 commands in .codebuddy, .claude, .qoder/`；根目录多出 `.codebuddy/`、`.claude/`、`.qoder/`、`openspec/` 四项。跑完需重启 IDE，斜杠命令才生效。

生成后 `openspec/config.yaml` 里的 `context:` 要手填项目技术栈与团队约定（AI 起草规范时会读它）。注意：1.11.0 生成的是 `config.yaml`，**不是**课程讲义里写的 `project.md`。

**`openspec/` 全项目只有一份，这是 SDD 的真相源。** 官方明确警告：`init` 在哪个目录跑就在哪生成 `openspec/`，**包括 monorepo 的子包目录**——所以禁止在 `backend/`、`frontend/`、`data_model/` 里跑 `init`，否则会凭空多出第二份规范，评审和追溯立刻失效。

后续成员：`npm i -g @fission-ai/openspec@1.11.0` → `git clone` → `openspec update`（**不要跑 `init` 再提交生成文件**）。若某人用的工具不在上表内，他才需要单独跑一次 `openspec init --tools "<他的工具id>"`；官方确认此操作对已存在的 `openspec/` 是安全的，不会动已有 specs 和 changes。

> 工程基线已于 2026-09-16 配置完成：分支保护（禁直推 / 禁强推 / 1 人审阅）、Squash 唯一、自动删分支、标签、协作者。

---

## 变更日志

| 日期 | 版本 | 变更人 | 主要变更 |
|---|---|---|---|
| 2026-10-06 | 1.1 | 苏哲勋 | 新增 §「自检：怎么确认这些设置真的生效」（承接 0911 周报「设置读不到、缺一份可自助核验的说明」）：给出五组**任何人都能跑**的核验命令与期望输出（仓库级设置 / ruleset / 标签 / 模板与协作者）；**更正 0911 的误诊** —— 「API 404」是查错了端点（保护用 ruleset 配，经典 `.../branches/main/protection` 恒返回 404），与权限无关；并记一条实测坑：**`git push --dry-run` 不触发服务端规则检查，不能拿来验证拦截**。另登记 ruleset 里两条清单未提的行为（推送后作废旧 Approve、未关联账号的提交需额外 Approve）。**正文章节与既有清单口径未改动，只增一节** |
| 2026-09-17 | 1.0 | 苏哲勋 | 补齐版本头与变更日志（**正文本轮一字未改**）：线的职责、目录结构、网页端设置清单、工具版本约定。正文「三条契约的归属」的回填由 PR #21（`898d965c`）完成，不计入本文件的变更 |

