# infra/ — 工程化与协作线

**负责人**：苏哲勋

## 职责

GitHub 仓库配置、分支规范与分支保护、PR / Issue 模板、CI 流水线、三条契约、缺陷管理。

## 交付物

契约文档、仓库规范、CI 配置、PR / Issue 模板。

## 边界

- `main` 分支受保护，禁止直接推送；合并前至少 1 位非作者审阅。
- CI 等有可测代码之后再接（`openspec validate` 也一并进流水线）。
- 只在本目录内写代码。

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

路径按工具名分开，三套文件同时存在不会相互覆盖；三款工具的斜杠命令拼法完全一致。

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
