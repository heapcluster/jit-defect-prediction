# 公开 JIT 缺陷数据集可下载性探测（PD-0 / change task 1.1–1.3）

> 探测时间：2026-10-24 15:40–15:55（UTC+8）｜ 探测人：蒋励（模型线）
> 探测方式：Zenodo REST API（`/api/records/{id}`）+ `curl` 直连下载，**无需登录、无需申请**；同时抽查文件真实可下载性与字段表头，不仅看页面是否可打开。
> 对应提案：`openspec/changes/public-dataset-quality/proposal.md`（课程附加功能 (3) 三条问题的回应）
> 结论：**部分可达** → 按 task 1.3 选定 1 个入 change（Trac），其余进候选清单备查。**未虚构任何数据**。

---

## 1. 候选清单与可达性

| # | 数据集 | 出处 | 可达性 | 体积 | 许可证 | 粒度 | 判定 |
|---|---|---|---|---|---|---|---|
| 1 | **Trac Dataset for JIT Defect Prediction** | Zenodo `3910003` | ✅ 200，实下 1.52 MB | CSV 1.5 MB / 12,840 行 | CC-BY-4.0 | **提交级** | **入选** |
| 2 | CPJITSDP v1.0（online cross-project JIT） | Zenodo `5994499` | ✅ 200 | zip 122 MB | other-open | 提交级（多项目流式） | 备查 |
| 3 | Large Defect Prediction Benchmark（8 corpora） | Zenodo `6342328` | ✅ 200 | zip 80.8 MB | other-open | **文件级** | 仅作粒度对照 |
| 4 | Investigation of Dataset Features for JIT | Zenodo `3772638` | ✅ 200 | 仅 1 个 PDF（0.4 MB） | CC-BY-4.0 | — | 无数据，备查 |
| 5 | ApacheJIT（106,674 changes，2003–2019） | 论文 arXiv:2203.00101 | ❌ 探测的 GitHub 仓库路径 404 | — | — | 提交级 | **不可达** |

补充说明（不粉饰）：

- **ApacheJIT 未获取到**。论文本身可读（arXiv 全文开放），但论文指向的数据仓库在常见路径下 404，未找到可用镜像；如需使用须联系作者或等待镜像恢复。这一点在周报中如实记录，不以「论文可读」冒充「数据可得」。
- **候选 3 的粒度不符**：`Large Defect Prediction Benchmark` 是 AEEEM / PROMISE 系的**文件级**静态度量数据集，没有提交哈希与 diff，**不能直接喂给本项目的 JIT 管线**；收录它只为「同一课程要求下的公开数据生态」做对照，不参与建模。
- 候选 4 只有论文附件 PDF，不是数据集，仅记入清单避免重复探测。

## 2. 字段完备性（以入选的 Trac 为准）

Trac 实测表头（15 列，12,840 行）：

```
commit, lines_of_code_added, lines_of_code_deleted, files_churned,
line_of_code_old, modified_subsystems, modified_subdirectories, entropy,
experience, rexp, number_of_authors, age, number_unique_changes,
purpose, defective
```

与契约一 / 契约二的映射：

| 契约字段 | Trac 列 | 状态 |
|---|---|---|
| `commit.commit_hash` | `commit` | ✅ 有，12,840 个互不重复 |
| `commit_label.is_bug_inducing` | `defective` | ✅ 有，0/1 二值，正样本 13.09% |
| `la` / `ld` | `lines_of_code_added` / `lines_of_code_deleted` | ✅ 有，无负值 |
| `entropy` / `exp` / `rexp` / `age` | 同名 | ✅ 有 |
| `nuc`（唯一作者数） | `number_of_authors` | 🔶 语义相近但口径需核对 |
| `ns` / `nf` | `number_unique_changes` / `files_churned` | 🔶 口径需核对 |
| `nd`（修改目录数） | `modified_subdirectories` | 🔶 近似 |
| `lt`（是否为修复提交） | — | ❌ **缺** |
| `sexp`（近期经验） | — | ❌ **缺** |
| `commit.commit_time`（提交时间戳） | — | ❌ **缺原始列**（只有 `age` 等派生量） |
| 变更文本 / diff | — | ❌ **缺** |

三条必须写清的边界：

1. **缺 diff 文本** → 语义线（CodeBERT 768 维）**无法在这个数据集上复现**，只能做「14 维表格特征 + 标签质量」的对照。这不是实现缺陷，是数据本身没有代码变更内容。
2. **缺提交时间戳** → 时间序切分只能靠 `age` 等派生量近似，或回到 Trac 源码仓库重建提交序列。若要用它做正式对照实验，必须先补这一列，否则「时间序一致」无法验证。
3. **标签粒度只有 0/1，无缺陷类型** → 正是课程指出的问题①，本项目**如实登记为「无缺陷类型」**，不伪造类型字段。

## 3. 选定与降级说明

- 按 task 1.3「字段完备性优先、语种多样性优先」：**Trac 入选**（提交级 + 标签 + Kamei 特征子集 + 非 Java 项目，直接支撑「突破 Java 单一语种」的论证）。
- CPJITSDP 备查：122 MB 含实现与多项目数据，适合后续做「跨项目不可迁移」的反面对照（Kamei et al. 2013 结论），本轮不下载入库，避免把 122 MB 塞进 `data/public/` 而使用率很低。
- **不触发 task 1.2 的整体降级**（因为确有可达且字段可用的数据集），但 ApacheJIT 这条「最贴近本项目的公开大数据集」不可得，需在报告与周报中如实列出。

## 4. 初步质量指标（仅 Trac，供 task 3.x 展开前的可行性判断）

| 指标 | 实测 | 说明 |
|---|---|---|
| 缺失率 | **0.00%**（15 列全无缺失） | 与课程问题③「数据不完整」形成对照：该数据集在这一项上是干净的 |
| 重复率 | **0 条**（`commit` 无重复） | 无「标签冲突」子项可查，但去重口径仍需在 3.4 显式声明 |
| 标签分布 | 正样本 **13.09%**（1,681 / 12,840） | 与本项目 Camel 基线（14.38%）同一量级，可比性尚可 |
| 字段一致性 | `la`/`ld` 无负值；`defective` 仅 {0,1} | 未发现越界值 |
| 时间序一致性 | **无法验证**（缺原始时间戳） | 已在 §2 第 2 条登记为阻塞项 |

## 5. 复现命令

```bash
# 元数据（含许可证、文件清单、体积）
curl -s https://zenodo.org/api/records/3910003

# 数据本体（1.5 MB，无需登录）
curl -L -o trac-dataset-nosexp.csv \
  "https://zenodo.org/records/3910003/files/trac-dataset-nosexp.csv?download=1"

# 字段与质量初检
python -c "import pandas as pd; d=pd.read_csv('trac-dataset-nosexp.csv',low_memory=False); \
print(len(d), d.isna().mean().max(), d['defective'].mean())"
```

## 6. 本轮结论

1. **PD-0 通过（部分可达）**：1 个提交级 + 有标签的数据集可用（Trac），1 个多项目备查（CPJITSDP），1 个粒度不符（Large Benchmark），1 个无数据（仅论文），1 个不可达（ApacheJIT）。
2. **可进入 task 2.x / 3.x**：加载器与质量评价以 Trac 为对象实现，`data/public/trac/` 落盘、不入库、不进交付链。
3. **两条硬边界先写死**：缺 diff 文本 → 语义线不在该数据集上复现；缺时间戳 → 时间序一致性指标需先补列或明确标「不可验证」。
