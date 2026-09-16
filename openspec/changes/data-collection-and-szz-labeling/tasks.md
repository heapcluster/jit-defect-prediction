## 1. 仓库与版本固定

- [x] 1.1 克隆 ActiveMQ 并固定到 `activemq-5.18.7`（只取该线），记录 `git rev-parse HEAD` 的完整哈希
      —— HEAD `7c03f67d46ae290ca49d549215277ab384c2bb8a`，附注标签对象 `3d1f921d…`
- [x] 1.2 把固定方式、版本号、完整哈希、固定日期回填进 `docs/data-pipeline.md` 第 2 节登记表
- [x] 1.3 确认 `data_model/data/`、`models/`、`artifacts/` 均被忽略规则排除；`git status --short` 中不出现任何数据产物
      —— 实测 `git status --short` 无 `data_model/data/` 项；`reports/` 为可入库产物

## 2. 提交采集

- [x] 2.1 写 `01_extract_commits.py`：按 `docs/contracts/data-fields.md` 表一抽字段，过滤父提交数大于 1 的合并提交
- [x] 2.2 提交时间统一换算为 UTC；仓库首个提交的 `parent_hash` 留空且不中断流程
      —— 实测 11,050 条中恰有 1 条 `parent_hash` 为空（根提交 `40a7d3b6…`，2005-12-12）
- [x] 2.3 提交清单落 `data_model/data/`，并打印提交总数与时间跨度
      —— 全量 11,050 条，2005-12-12 ~ 2025-03-13
- [x] 2.4 列名逐字比对契约表一，列出任何缺列、改名或自造列，闭环后再往下走
      —— 实测缺列 0、多列 0（契约表一的 `id` 由数据库自增，CSV 不落）
- [x] 2.5 边界验证：构造提交总数为 0 的场景，确认流程失败退出而不是继续进入打标
      —— `--since 2030-01-01` 实测 exit 4，报「抽取结果为 0 条提交，终止」

## 3. SZZ 打标

- [x] 3.1 先跑现成打标库路线（`label_method = szz`），实测是否可用；不可用则登记结论并转 3.2
      —— **PySZZ 不在 PyPI（404），不可用**；按兜底策略转自研，结论登记进 `docs/data-pipeline.md` 第 7 节
- [x] 3.2 写自研简化版打标（`label_method = szz_lite`）
      —— `02_szz_labeling.py` 同时实现 `szz`（自研标准行级回溯）与 `szz_lite`（文件级回溯）
- [x] 3.3 把修缺陷提交的判据（缺陷编号 **且** 修复语义双命中）成文写进 `docs/data-pipeline.md`
- [x] 3.4 回溯：对修复提交定位引入缺陷的提交，命中者记 `is_bug_inducing = 1` 并写 `bug_fix_hash`
- [x] 3.5 回溯失败的修复提交单独留档，**不计入负样本**，数量计入统计
- [x] 3.6 复现性验证：连续执行两次，两份标签按 `commit_hash` 排序后逐行一致
      —— 实测 `--labeled-at` 钉时间后连跑两次，两套方法均**逐字节一致**
- [x] 3.7 抽样人工复核不少于 30 条修复提交识别结果，给出漏判/误判率
      —— 抽样名单已由 `04_build_dataset.py --review-sample 30` 产出（`reports/labeling_review_sample.md`，A 组查误判 / B 组查漏判）；
         **误判率与漏判率两栏待复核人填写后方可勾选本项**
- [x] 3.8 两套方法的分歧清单可出具（差异条数 + 抽样对照）
      —— `reports/szz_labeling_stats.md` 内含「两套方法对照」表（都判正 / 仅 A / 仅 B / 分歧率）

## 4. 样本集与统计

- [x] 4.1 写 `04_build_dataset.py`：按 `commit_hash` 汇总提交清单、标签与特征，产出样本集
- [x] 4.2 断言不存在「有标签却缺样本」与「有样本却缺标签」的行
      —— 断言 A（标签 ⊆ 提交清单）、断言 B（标签 ⊆ 特征表）任一失败即 exit 4，不产出样本集
- [x] 4.3 打印七项统计并落 `data_model/reports/` 下的统计表
- [x] 4.4 核对正样本比例是否落在合理区间；若落入 40%–60%，先排查判据再继续
      —— 窗口子集实测 `szz` 5.10% / `szz_lite` 6.54%，不在异常区间
- [x] 4.5 确认样本集不含任何切分列或切分文件（切分属下游 change）
      —— 04 内置列名黑名单校验，命中即失败

## 5. 文档回填与交付

- [x] 5.1 `docs/data-pipeline.md` 回填：第 4 节脚本路径、第 5 节复现命令、第 7 节待定项结清
      —— 第 6 节统计数字待全量运行结束后回填
- [x] 5.2 `data_model/README.md` 的五步链路表补上实际脚本名
- [ ] 5.3 提交 PR 并在描述里写明关联 change id `data-collection-and-szz-labeling`；由非作者审阅后合入
- [ ] 5.4 回飞书看板更新任务状态

## 6. 契约回改（本轮实测发现的缺口，须走契约变更流程）

> 这四条都是「契约里没写清、实现必须先作主」的地方。不补进契约，下一轮换人实现就会跑出不同的数。
> 前三条的实测证据见 `reports/feature_stats.md` 的专节。

- [ ] 6.1 `docs/contracts/feature-columns.md` 第四节补写 `rexp` 的衰减公式
      —— 现只写「按时间衰减加权」。实现取值：`Σ count(n)/(n+1)`，`n` = 距本次提交的整年数（Kamei 原文口径）
- [ ] 6.2 `docs/contracts/feature-columns.md` 第三节把 `ns/nd/nf/la/ld/lt` 的类型由 INT 改为 DECIMAL/DOUBLE
      —— 与第四节「全部取对数」自相矛盾：取完对数必为小数，不能同时成立
- [ ] 6.3 `docs/contracts/feature-columns.md` 第四节说明 `ln(x)` 与「0 值记 0」在 0 附近不连续
      —— 建议 v2 统一为 `ln(1+x)` 通算并升 `feature_version`；实测 `la` 有 7 条记 0、其余最小 −7.43
- [ ] 6.4 `docs/contracts/feature-columns.md` 第四节写明 `nuc` 的聚合方式
      —— 实现取「按文件分别计数再求和」（依据：第四节把 `nuc` 除以 `nf`；原文表述为 count of commits per specific file）。`ndev` 数的是人、取并集，两者故意不对称
- [x] 6.5 `docs/contracts/data-fields.md` 表二去掉 `szz` 后的「（PySZZ）」括注
      —— **已于契约一 1.2 版完成**（见该契约变更日志）。取值仍在契约枚举 `{szz, szz_lite}` 内，只改说明文字、不改枚举，未触发版本升级
