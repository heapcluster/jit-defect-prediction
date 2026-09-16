# 新成员上手清单

> 版本 1.4 ｜ 创建 2026-09-16 ｜ 维护：全员公共 ｜ 审核 蒋励
> 目标：**照做约 20 分钟**，你的机器就能跑起这个项目，并且知道动手前该读什么。

## 0. 你机器上要有这三个东西

| 工具 | 版本要求 | 怎么确认 |
|---|---|---|
| Git | 任意较新版本 | `git --version` |
| Node.js | **≥ 20.19.0** | `node --version` |
| Python | **3.12.x** | `python -V` |

Node.js 不是可选项 —— OpenSpec CLI 是 npm 包，靠它装。

Python **用哪种工具管理由你自己定**（conda / venv / uv / pyenv 都行），只要版本对得上。见第 2 节。

## 1. 拿到代码

```bash
git clone https://github.com/jolly326/jit-defect-prediction.git
cd jit-defect-prediction
ls
```

看到这六个目录就对了：`data_model` `backend` `frontend` `infra` `docs` `openspec`。

根目录还会看到 `README.md`、`AGENTS.md`、`CLAUDE.md`、`.github/`，以及三套 AI 工具目录 `.codebuddy/`、`.claude/`、`.qoder/`（点号开头，要 `ls -a` 才显示）。

**不要**把仓库 clone 到中文路径或带空格的路径下，`pip` 与 `npm` 偶尔会在这种路径上出问题。

## 2. 建 Python 环境（只做一次）

**全组统一的是「版本」和「依赖清单」，不是工具，也不是环境名。**

| 必须一致 | 不必一致 |
|---|---|
| Python **3.12.x** | 用 conda / venv / uv / pyenv 中的哪一种 |
| 依赖清单与版本（各线 `requirements.txt`） | 环境叫什么名字、建在哪个路径 |

会造出「本地能跑、别人跑不了」的是**版本与依赖不一致**，不是工具不一致。所以不强求所有人用 conda，也不要求环境同名 —— 你机器上已经有什么就用什么。

**任选一种建环境：**

```bash
# 方式一：venv（Python 自带，最省事）
python -m venv .venv
source .venv/Scripts/activate      # Git Bash
.venv\Scripts\activate             # PowerShell / cmd

# 方式二：conda（本机已装 conda 的话）
conda create -n jit python=3.12 -y
conda activate jit

# 方式三：uv（速度最快，需另装 uv）
uv venv --python 3.12
```

激活后**先确认版本**，再装依赖：

```bash
python -V       # 必须是 3.12.x，不是就先别往下走
```

| 线 | 主要依赖 | 依赖清单 |
|---|---|---|
| 数据与模型 | `pandas numpy scikit-learn xgboost GitPython` | `data_model/requirements.txt` |
| 后端与接口 | `fastapi uvicorn sqlalchemy pymysql python-dotenv` | `backend/requirements.txt` |
| 前端与可视化 | 走 npm | `frontend/package.json` |
| 工程与证据 | 无 | — |

> **依赖清单文件目前尚未建立**，眼下以本表为准。建立后一律以文件为准：谁改动依赖谁加一行，`pip install -r requirements.txt` 一把装齐，避免每人装出一个不同版本。

数据集与模型文件**一律不入库**。`.gitignore` 已经挡好，不要用 `git add -f` 强行加。

**环境目录也不入库**：`.gitignore` 已排除 `.venv/` 与 `venv/`；conda 环境建在仓库外，同样无需处理。你列 `git status` 时看到自己的环境目录，说明建错位置了。

## 3. 装 OpenSpec CLI（每人自己装，但版本必须一致）

**你用哪款 AI 编码工具都行** —— 组内常用的三款（CodeBuddy、Claude Code、Qoder）都已在仓库里配置好，斜杠命令拼法一致，都是 `/opsx:propose`。用的是别的工具才需要多做一步（见下面第 2 条）。

```bash
npm install -g @fission-ai/openspec@1.11.0   # 带死版本号，不要用 @latest
openspec --version                            # 必须输出 1.11.0

cd <仓库根目录>
openspec update                               # 生成你自己那套工具的斜杠命令
```

三个坑，逐条注意：

1. **版本必须锁 1.11.0。** `openspec update` 是按*本机 CLI 版本*重新生成命令文件的，谁版本不一致，谁就能把别人的新命令覆盖回旧版。要升级先在全组说一声。
2. **不要跑 `openspec init`。** 组长已经在仓库根跑过，`openspec/` 与三套工具目录都已入库。只有当你的 AI 工具**不属于**上面那三款时，才需要跑一次 `openspec init --tools "<你的工具id>"` —— 而且**必须在仓库根目录**（详见第 7 节）。
3. **`init` 的 `--tools` 在 PowerShell 下必须加引号**（`update` 用不到这个参数，可以忽略）。

## 4. 自检：四条都过才算环境就绪

```bash
git status --short                          # 应为空（你没改过任何文件）
python -V                                   # 3.12.x
openspec --version                          # 1.11.0
ls -d .codebuddy .claude .qoder openspec    # 四项都在
```

有一条不过就先别开工 —— 环境问题拖到写代码时才发现，会误判成代码问题。

## 5. 开工前按顺序读这六份（约 25 分钟）

> **先分清两件事**：这周做什么、需求是什么 —— 在**飞书**；代码怎么写、字段叫什么 —— 在**仓库**。仓库文档里没有任务清单，这不是遗漏。

| 顺序 | 读什么 | 为什么读它 |
|---|---|---|
| 1 | `AGENTS.md` | **所有 AI 编码工具的统一规则入口**（CodeBuddy、Claude Code、Qoder 都读它）。开头就写了「任务与需求在飞书」的权威边界。**改完必须开新会话才生效** |
| 2 | **飞书《工作周报-YYYYMMDD》** | **你这周该做什么、怎么算做完** —— 去飞书看，仓库里没有 |
| 3 | **`docs/dev-handbook.md`** | 这件事在代码里具体怎么做、跑什么命令、验收什么、怎么让 AI 帮你做 |
| 4 | `docs/collaboration.md` | 分支怎么切怎么合、提交怎么写、PR 怎么提、**谁审谁合**、代码怎么写（开发规范） |
| 5 | `docs/sprint0-scope.md` | 代码边界：做什么、**不做什么**、四条线边界、冻结点、完成定义 |
| 6 | `docs/contracts/` | 三份契约：数据字段 / 特征列名 / 接口格式。前端还要加读 `docs/pages.md` |

要动手改哪条线，再读那条线目录下的 `README.md`。**不必通读全部文档** —— 按需查。

## 6. 第一次提交的标准动作

```bash
git checkout -b feat/backend/predict-api      # 分支命名：<类型>/<线>/<简述>
# 写代码
git add backend/app/api/predict.py            # 加具体文件，不要 git add .
git commit -m "feat(backend): 新增预测接口"
git push -u origin feat/backend/predict-api
```

然后：网页开 PR → 模板自动带出四项 → 找**苏哲勋（infra 线）**审 → Squash merge → **回飞书看板更新状态**。

看板不更新等于没做，而且这部分是课程评分点。

## 7. 六个已知的坑

| 坑 | 你看到的现象 | 怎么办 |
|---|---|---|
| PowerShell 里逗号被当数组分隔符 | `Invalid tool(s): codebuddy claude qoder` —— 三个 id 明明都在可用列表里，却报无效 | 加引号：`--tools "codebuddy,claude,qoder"`。bash / Git Bash 无此问题 |
| 在子目录跑 `openspec init` | 仓库里凭空多出第二份 `openspec/`，评审与追溯失效，且很晚才会发现 | **只在仓库根目录跑**。`backend/`、`frontend/`、`data_model/` 里绝对不能跑 |
| 误提交数据集 / 模型文件 / `.env` | PR 被拒，或仓库体积暴涨 | `.gitignore` 已挡；不要 `git add -f` |
| AI 助手说「没看到项目规则」 | 规则没生效 | 规则只在**会话启动时**注入 → 开新会话。Claude Code 首次遇到 `@AGENTS.md` 会弹批准框，必须点「允许」，选拒绝会被永久禁用 |
| 随机切分训练集与检验集 | 指标虚高，模型上线后完全不灵 | 必须按 `committed_at` **时间序**切（前 70% 训练、后 30% 检验） |
| 直接往 `main` 推 | 被分支保护拒绝 | 走分支 + PR，这是设计如此 |
| 别人的环境跑不起来 | 报 `ModuleNotFoundError`，或版本不兼容 | 先对 `python -V`（必须 3.12.x），再按该线 `requirements.txt` 重装。**不要「在我机器上装好了」就推代码** |

## 8. 卡住了找谁

| 问题类型 | 找谁 |
|---|---|
| 环境、依赖、跑不起来 | 对应线的负责人，或 `infra` 线（苏哲勋） |
| 接口 / 字段 / 特征列名对不上 | 先看 `docs/contracts/`，仍不清楚就开 Issue，不要自己改约定 |
| 需求本身有歧义 | 先看飞书《产品需求文档》；仍不清就找蒋励（统稿），他会更新飞书文档或提 change |
| 不确定该不该做 | 开 Issue 问，**不要先做再问** |

## 变更日志

| 日期 | 版本 | 变更人 | 主要变更 |
|---|---|---|---|
| 2026-09-16 | 1.0 | 蒋励 | 初版建立：环境、OpenSpec CLI、自检、阅读顺序、首次提交、六个坑 |
| 2026-09-16 | 1.1 | 蒋励 | **解绑 Python 环境工具**：不再强制 conda 与环境名，改为「统一 Python 版本与依赖清单，工具各人自选」；补 venv / uv 两种等价方式；AI 工具表述改为中立；坑表增至七条 |
| 2026-09-16 | 1.2 | 蒋励 | 同步协作规范的审阅简化：第 6 节的审阅人由「配对的人」改为**苏哲勋（infra 线）**；第 5 节对 `collaboration.md` 的说明补上「分支操作」与「开发规范」 |
| 2026-09-16 | 1.3 | 蒋励 | 第 5 节阅读顺序纳入 **`docs/task-guide.md`**（开工第一份），由五份增至六份 |
| 2026-09-16 | 1.4 | 蒋励 | **按权威边界调整**：阅读顺序第 2 项改为**飞书《工作周报》**（任务不在仓库），第 3 项由 `task-guide.md` 更名后的 `dev-handbook.md` 承接；第 8 节「需求有歧义」改为先查飞书需求文档 |
