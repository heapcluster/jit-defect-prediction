# 数据链路与版本固定

> 状态：**进行中，第 ① 步已完成** ｜ 版本 0.93 ｜ 负责人 蒋励 ｜ 冻结时间 Sprint 0 末（9/25）

## 0. 这份文档解决什么问题

**Sprint 0 第 2 号交付物的验收依据就是本文。** 交付物写的是「有可复现脚本，且报出样本总数与正负样本比例」—— 没有本文，评审时无法判断脚本是否真的可复现、比例数字从哪来。

三件事写在这里，不写在别处：

1. 数据从哪来、**固定在哪个版本**（版本会漂移，不 pin 就没有可复现性）
2. 数据落在哪个路径、哪些入库哪些不入库
3. 每一步的脚本入口、复现命令、必须报出的统计

## 1. 数据源

| 项 | 值 |
|---|---|
| 仓库 | `https://github.com/apache/activemq.git` |
| 仓库名（写入数据库 `commit.repo_name`） | `activemq` |
| 本期范围 | **只用这一个仓库**，不做跨仓库训练与对比（见 `sprint0-scope.md` 第 2 节） |

## 2. 版本固定（最重要的一条）

**必须固定到某一个发布 tag 或 commit，不要用 `main`。**

`main` 每天都在变。两个月后同一个脚本跑出不同的数据集，「上次的 F1 是 0.72」这句话就无法解释 —— 是模型变了、还是数据变了，分不清。

```bash
git clone --single-branch --branch <TAG> https://github.com/apache/activemq.git activemq
cd activemq
git describe --tags              # 确认落在预期 tag 上
git rev-parse HEAD               # 把输出的完整哈希抄进下表
```

> 加 `--single-branch --branch <TAG>` 而不是裸 clone：只取该条线的历史，把仓库体积从「全部分支」压到 139 MB 左右，且**同样精确固定到该 tag 指向的提交**。注意 `activemq-5.18.7` 是**附注标签（annotated tag）**，`git ls-remote` 给出的对象哈希是标签对象、不是提交 —— 登记表里必须写 `git rev-parse HEAD` 得到的**提交哈希**。

**固定信息登记**（2026-09-16 回填，此后任何改动都要在变更日志里记一笔）：

| 项 | 值 |
|---|---|
| 固定方式 | tag（附注标签 `activemq-5.18.7`，标签对象哈希 `3d1f921dd56a91b29028a099ef79fec1ab01b644`） |
| 固定版本号 | `activemq-5.18.7` |
| **完整 commit 哈希** | **`7c03f67d46ae290ca49d549215277ab384c2bb8a`** |
| 固定日期 | 2026-09-16 |
| 抽取到的提交总数 | **11,050**（已过滤 566 条合并提交；含合并提交时为 11,616） |
| 提交时间跨度 | 2005-12-12 ~ 2025-03-13 |
| 仓库体积 / 检出文件数 | 139 MB / 5,334 个文件 |

**为什么选 5.18.7**：6.x 起包名迁移到 `jakarta.*`，与 5.x 历史之间做跨版本代码解析会引入额外噪声；5.17.x 更早已停止维护、可用的缺陷修复提交更少。5.18 是 5.x 最后一条稳定线且历史连续，5.18.7 是该线最新补丁发布。

> ⚠️ **一个必须留意的数据质量点**：本版历史回溯到 2005 年，其中 2005–2013 段来自 SVN 迁移，提交信息格式与 `git blame` 行为都不典型（见下方原「选版本的经验」）。**若打标结果显示早期提交的标签质量明显偏低，按第 7 节的窗口裁剪预案处理**（裁剪口径与理由同样要登记在本节）。

> 选版本的经验（保留备查）：太老的版本用 SVN→Git 迁移历史，提交信息格式与 `git blame` 行为都不典型；太新的版本提交量少、缺陷标注样本不足。**建议选一个已停止维护的较新稳定分支** —— 本次选 5.18.7 即按此判断。

## 3. 数据落盘路径

| 路径 | 内容 | 入库？ |
|---|---|---|
| `data_model/data/` | ActiveMQ 仓库副本、抽取出的中间数据 | ❌ 已被 `.gitignore` 的 `data/` 规则排除 |
| `data_model/models/` | 训练出的模型文件 | ❌ 已被 `models/` 与 `*.pkl` / `*.joblib` 排除 |
| `data_model/reports/` | 小体积统计结果（样本数、比例、指标表） | ✅ **可入库** —— 这是给别人比对的证据，路径不在忽略名单内 |
| `data_model/artifacts/` | 中间产物、缓存 | ❌ 已被 `artifacts/` 排除 |

**不要为了提交数据而改 `.gitignore`，也不要用 `git add -f`。** 数据集与模型文件不入库是课程的硬要求，也是 `.gitignore` 第一节就写死的东西。

## 4. 链路五步

```
① 克隆并固定版本  →  ② 抽取提交  →  ③ SZZ 打标  →  ④ 算 Kamei 14 项特征  →  ⑤ 输出样本集
```

| 步 | 做什么 | 脚本入口 | 输出 |
|---|---|---|---|
| ① | 克隆 + checkout 到固定版本 | 手工执行，命令见第 2 节 | `data_model/data/activemq/` |
| ② | 读提交记录（GitPython），过滤合并提交 | `data_model/01_extract_commits.py` | `data_model/data/commits.csv` + `reports/commit_extract_stats.md` |
| ③ | SZZ 打标：找出「修复提交」并回溯到引入缺陷的那次提交 | `data_model/02_szz_labeling.py` | `data_model/data/commit_labels_{szz,szz_lite}.csv` + `reports/szz_labeling_stats.md` |
| ④ | 按 `contracts/feature-columns.md` 算 14 项特征 | `data_model/03_extract_features.py` | `data_model/data/commit_features.csv` + `reports/feature_stats.md` |
| ⑤ | 汇总成一份可训练样本集 | `data_model/04_build_dataset.py` | `data_model/data/dataset_{szz,szz_lite}.csv` + `reports/dataset_stats.md` |

**② 与 ③ 的字段口径以契约为准**，不要自己发明列名：

- 提交与标签字段 → `docs/contracts/data-fields.md`
- 特征列名与取值口径 → `docs/contracts/feature-columns.md`（第四节「取值口径」已于 2026-09-16 冻结为 `feature_version = v1`，**可以开始跑特征**；口径若再改，升 `v2` 并全量重算，不覆盖 v1）

**④ 与 ⑤ 的脚本编号顺序即执行顺序**，不要跳步：⑤ 的三条断言依赖 ③ 与 ④ 的产物在同一窗口上产出。

**03 也有 `--since`**：它的作用与 01 的不同 —— 01 的 `--since` 决定「哪些提交进样本」，03 的 `--since` 只决定「给哪些提交算特征」，**历史类特征始终用完整历史**（`ndev`/`age`/`nuc`/`exp`/`rexp`/`sexp` 看得见窗口之前的全部提交）。两个 `--since` 必须传同一个值，否则 ⑤ 的断言 B 会失败退出。

## 5. 复现命令

从干净 clone 开始，按顺序执行即可得到与第 6 节一致的样本集。

```bash
# 0. 环境：Python 3.12.x + 按 data_model/requirements.txt 装依赖
#    （环境工具自选：conda / venv / uv 均可，见 docs/onboarding.md 第 2 节）
#    本组验证用的环境：conda env `jit-defect`（Python 3.12.14）
#      conda create -n jit-defect python=3.12 -y
#      conda run -n jit-defect python -m pip install -r data_model/requirements.txt
cd data_model

# ① 固定数据版本（手工执行一次；克隆到 data/activemq/，命令见第 2 节）
#    确认落在登记版本上：
git -C data/activemq rev-parse HEAD     # 必须等于 7c03f67d46ae290ca49d549215277ab384c2bb8a

# ② 抽取提交（过滤合并提交，校验 HEAD 与登记一致）
python 01_extract_commits.py

# ③ SZZ 打标（两套方法各打一次，产出可比对的标签）
python 02_szz_labeling.py --method both

# ④ 特征计算（14 项，口径 v1）
python 03_extract_features.py

# ⑤ 汇总样本集并打印七项统计
python 04_build_dataset.py \
  --labels data/commit_labels_szz.csv \
  --labels data/commit_labels_szz_lite.csv
```

**只想先验证链路通不通**（约 1 分钟，不必等全量打标）：给 ② 加窗口、③ 加运行标记、④ 传同一个窗口，⑤ 用带标记的标签文件。

```bash
python 01_extract_commits.py --since 2023-01-01 --out data/commits_window2023.csv
python 02_szz_labeling.py --commits data/commits_window2023.csv --tag window2023 --method both
python 03_extract_features.py --commits data/commits_window2023.csv --since 2023-01-01 \
  --out data/commit_features_window2023.csv --raw data/commit_features_raw_window2023.csv
python 04_build_dataset.py --commits data/commits_window2023.csv \
  --features data/commit_features_window2023.csv \
  --labels data/commit_labels_window2023_szz.csv \
  --labels data/commit_labels_window2023_szz_lite.csv --tag window2023
```

> 子集运行不要在 ③ 的判据自检上纠结：`docs/data-pipeline.md` 第 7 节登记的外沿数字是在**完整版本**上算的，子集对不上是正常的，报告里会标「不可比」。

**复现的两条前提**（缺一条就不是可复现）：① 数据已固定到第 2 节登记的版本；② 依赖按 `requirements.txt` 装，而不是「我机器上有什么用什么」。

**验收标准**：别人在你之外的一台机器上，照上面五条命令跑完，得到与第 6 节完全一致的统计数字（允许 ±0，因为版本已固定）。

## 6. 必须报出的统计（第 6 项交付物的证据）

跑完后把这张表填好，存进 `data_model/reports/`，同一份贴进周报：

| 指标 | 值 | 说明 |
|---|---|---|
| 总提交数 | 待回填 | 过滤合并提交之后的数 |
| 时间跨度 | 待回填 | 最早 ~ 最晚提交时间 |
| 打标成功数 | 待回填 | 能判定标签的提交数 |
| **正样本数**（引入缺陷） | 待回填 | `is_bug_inducing = 1` |
| 负样本数 | 待回填 | `is_bug_inducing = 0` |
| **正样本比例** | 待回填 | 正样本数 ÷ 打标成功数 |
| 打标方法 | 待回填 | `szz` 或 `szz_lite`（见 `contracts/data-fields.md` 表二） |

**正样本比例是判断数据是否可用的第一个信号。** 经验上 JIT 数据集的正样本比例很低（个位数到十几个百分点），若算出来接近 50%，多半是打标逻辑出了问题，先查再往下走。

## 7. 待定项（悬着的事写在这里，不留在聊天记录里）

| # | 待定 | 影响 | 谁来定 | 什么时候 | 状态 |
|---|---|---|---|---|---|
| 1 | PySZZ 是否可用 | 打标方式：现成库 vs 自研简化版 | 蒋励实测 | Sprint 0 内 | ✅ **已定**：PySZZ 不在 PyPI（实测 404），按兜底策略切自研，详见下方 |
| 2 | 固定到哪个 tag / commit | 可复现性的基准 | 蒋励 | 首次跑通时 | ✅ **已定**：`activemq-5.18.7`，见第 2 节 |
| 3 | `contracts/feature-columns.md` 第四节的取值口径 | 特征数值量级，未定稿前不大量重算 | 蒋励 | 9/18 前 | ✅ **已定**：契约二第四节已冻结（采用原文口径 + 对数变换三条补充） |
| 4 | 是否需要记录「修改文件列表」子表 | 特征计算的输入完整性 | 蒋励 + 吕建江 | 特征计算时发现 | ✅ **已定**：不记入 `commit` 表，文件级明细由数据线中间产物承载、不入库（见契约一冻结结论） |
| 5 | 是否裁剪时间窗口 | 全量打标的耗时与样本量 | 蒋励 | 首次全量实测后 | **新增，未决** —— 全量 11,050 条提交做回溯的开销尚未实测，若超出 Sprint 0 预算则按本节预案裁剪 |

**第 1 项的裁定结论（2026-09-16 实测）**：**PySZZ 不在 PyPI**（`https://pypi.org/pypi/pyszz/json` 返回 404；同批探测 `pydriller` 正常返回 200，排除网络因素）。其官方仓库依赖预先生成的 `gitlog` 数据格式，属研究专用工具，在 Sprint 0 内跑通不现实。按原兜底策略执行：

- `label_method = 'szz'` —— 由 `02_szz_labeling.py` **自研实现标准行级 SZZ**（对修复提交改动掉的每一行在父提交上做 `git blame`），**不是** PySZZ
- `label_method = 'szz_lite'` —— 自研文件级回溯简化版（只看被改文件在父提交时的最后一次改动），快一个量级、粒度更粗
- 两套结果都保留，差异量化后出示（见 `reports/szz_labeling_stats.md`），不静默取其一

> ⚠️ **连带要改契约一**：`docs/contracts/data-fields.md` 表二把 `szz` 标注为「（PySZZ）」，该括注已不成立，需改掉。取值仍在契约定义的集合 `{szz, szz_lite}` 内，故只改说明文字、不改枚举，不触发 `feature_version` 升级。

**第 5 项的裁定口径（预案）**：裁剪是**下策**，因为会改变样本量级、削弱与文献的可比性。只有在①全量实测明显跑不完 Sprint 0，且②已尝试过分片与缓存优化之后才启用。一旦启用，必须在本节登记**裁剪起止时间、保留的提交数、裁剪理由**，并同步升 `feature_version`。

### 打标判据（2026-09-16 实测重登记）

修缺陷提交的判据（见 `openspec/changes/data-collection-and-szz-labeling/design.md` 决策 D4）：**缺陷编号 与 修复语义 双命中**。规格 `szz-labeling` 要求判据必须写成文字、不能只活在实现代码里，故完整口径登记如下 —— **修复语义词必须落在词首边界**：

> **判据 D4** = 提交信息匹配 `AMQ-\d+` **且** 匹配 `\b(fix|bug|patch)`（大小写不敏感）。

在固定版本（11,050 条非合并提交）上按提交信息直接统计，得到判据的命中外沿：

| 判据 | 命中数 | 占 11,050 条非合并提交 |
|---|---|---|
| 只要求含 `AMQ-<数字>` 编号 | 6,042 | 54.7% |
| 编号 **且** 含 `fix`/`bug`/`patch`（词首边界） | 2,417 | 21.9% |
| 编号 **且** 含 `fix` 词形（词首边界） | 1,939 | 17.5% |

**为什么要卡词首边界**：`dispatch` / `debug` / `prefix` 这三个词天然含 `patch` / `bug` / `fix` 子串，而「消息分发（dispatch）」恰是 ActiveMQ 的核心功能词。2026-09-16 实测：用子串匹配会多收 **122 条**这样的提交（dispatch 词族 83、debug 17、prefix 9，其余同类），**没有一条是真修复**；反过来收窄成「严格词表」（只认 fix/fixes/fixed/bug/patch 的完整词）又会漏掉 `fixe` / `fixinng` / `patchh` 这类**拼写错误的真修复**。词首边界取二者中点 —— 保留词形变化（fixes / fixed / patching / bugfix），排除同词内嵌（dispatch / debug / prefix）。

**这组数字说明两件事**：① 用「只含编号」当判据会把 54.7% 的提交都拉进候选池，包含大量新功能与文档提交 —— 印证了必须加修复语义这一条；② 打标成功的提交数上限在 1,939 ~ 2,417 之间，**正样本比例不可能接近 50%**，与 JIT 研究的经验区间一致。

> 上表是**未做溯源过滤**的外沿。真实正样本数还要经过 `git blame` 回溯：只有被修复代码行能定位到引入方的提交才会记 `is_bug_inducing = 1`，回溯失败的那批会被排除、不记 0（见 `design.md` 决策 D5）。因此最终的正样本比例会低于上表。

> **关于旧登记值（6,041 / 2,538 / 1,865）**：本节原先是「预跑探测」的三个值，2026-09-16 重登记，原因两条 —— ① 旧值**无法从当前提交清单复现**（`fix` 词形口径实测为 1,939，任何自然正则都算不出 1,865），而 `02_szz_labeling.py` 的自检要求逐项相等，登记值不可复算就等于自检形同虚设；② 其中 2,538 用的是**子串**口径，含上述 122 条假阳性。旧值在此留档备查，**不删除**。重登记后全量运行的自检会逐项相等。

## 变更日志

| 日期 | 版本 | 变更人 | 主要变更 |
|---|---|---|---|
| 2026-09-16 | 0.9 | 蒋励 | 初版骨架：数据源、版本固定、落盘路径、四步链路、复现与统计要求、待定项 |
| 2026-09-16 | 0.91 | 蒋励 | 复现命令去除绑定的环境名，改为「Python 3.12.x + `requirements.txt`」（环境工具各人自选）；补「可复现的两条前提」 |
| 2026-09-16 | 0.92 | 蒋励 | **第 ① 步（克隆并固定版本）完成**：回填固定信息登记表（tag `activemq-5.18.7`、提交哈希 `7c03f67…`、11,050 条非合并提交、跨度 2005-12-12~2025-03-13、139 MB）；克隆命令补 `--single-branch` 与「附注标签的远程哈希不是提交哈希」这条坑；新增「为什么选 5.18.7」与 SVN 迁移段的数据质量提醒；§7 待定项第 2、3、4 项结清并新增第 5 项「是否裁剪时间窗口」（含裁定口径预案）；新增「打标判据（预跑探测）」表 —— 编号+修复语义双命中的外沿为 23.0%，印证正样本比例不会接近 50% |
| 2026-09-16 | 0.93 | 蒋励 | **判据口径定死并把外沿数字重登记为可复现值**：D4 的修复语义一项明确为**词首边界** `\b(fix\|bug\|patch)`（子串会误收 122 条 dispatch/debug/prefix 提交，全部为假阳性；严格词表又会漏掉 fixe/fixinng/patchh 这类拼错的真修复）；外沿由 6,041/2,538/1,865 改为 **6,042/2,417/1,939**，旧值留档并说明重登记原因（旧值无法复现，且 `02` 的自检要求逐项相等）；`02_szz_labeling.py` 与 `04_build_dataset.py` 的判据文字同步 |
