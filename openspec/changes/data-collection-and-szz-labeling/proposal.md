# 数据采集与 SZZ 打标

> Sprint 0 ｜ 对应飞书《工作周报-20260911》任务 3（建首个 change）与任务 6（拉通数据链路）
> 起草 2026-09-16 ｜ 起草人 蒋励 ｜ 关联契约：`docs/contracts/data-fields.md`

## Why

模型线、后端线、前端线都在等同一份东西：**一份可复现、带缺陷标签的提交样本集**。仓库现在只有契约与说明文档，`data_model/` 下没有任何可执行代码 —— 链路一天不通，后端的三张表就没有数据可灌，前端的三个页面就没有内容可画。

更要紧的是时序。这份代码里藏着三个**不可逆的口径决定**：固定到哪个版本、合并提交怎么处理、SZZ 用哪套算法。先写代码后补规格，口径就会散落在实现细节里；等两个月后同一个脚本跑出不同的数字，没人说得清「上周那个 F1 对应的是哪份数据」。

## What Changes

- **新增「提交采集」能力**：从 `https://github.com/apache/activemq.git` 抽取提交清单；仓库副本固定到登记在册的 tag（不使用浮动的 `main`）；过滤合并提交；字段与命名照 `docs/contracts/data-fields.md` 表一
- **新增「SZZ 打标」能力**：识别修缺陷提交（fix commit），回溯出引入缺陷的那次提交，产出 `commit_label` 表；`label_method` 区分 `szz`（PySZZ）与 `szz_lite`（自研简化版），两套结果都保留以便对照
- **新增「带标签样本集」能力**：把提交清单与标签汇成一份可训练样本集，报出总提交数、时间跨度、正/负样本数与**正样本比例**；统计表落 `data_model/reports/`
- **新增可复现命令**：`data_model/` 下按 `01_xxx.py` 编号的脚本，并把固定版本、脚本路径、复现命令与统计数字回填进 `docs/data-pipeline.md`
- **落盘边界落到实现**：数据集与模型文件不入库 —— 沿用现有 `.gitignore`，**不新增排除规则、不使用 `git add -f`**

**不做什么（显式列出）**

- **不做** Kamei 14 项特征计算与模型训练 —— 特征取值口径尚未冻结（见 `docs/contracts/feature-columns.md` 第四节），另开 change
- **不做** 跨仓库训练与对比 —— 本期只用 ActiveMQ 单仓库
- **不做** CI 强制拦截 —— 本系统只做建议性预警，不阻塞开发
- **不改** `docs/contracts/` 的字段名与列名 —— 本 change 只实现契约，不发明字段（契约的冻结动作属周报任务 5，不在本 change 范围）
- **不引入** 新数据源，不做数据增强、不做标签合成

**是否触及 `docs/sprint0-scope.md` 的边界**：**不触及**。本 change 落在该文第 2 节「做」的前两条（单仓库 ActiveMQ 固定版本、SZZ 打标含自研简化版对照）之内，不改变系统定位、不改变四条线的目录边界。

## Capabilities

### New Capabilities

- `commit-collection`: 把 ActiveMQ 仓库副本固定到登记在册的版本，抽取提交清单并过滤合并提交，按契约落字段与索引
- `szz-labeling`: 识别修缺陷提交并回溯出引入缺陷的那次提交，产出带 `label_method` 的缺陷标签，支持两套方法对照
- `labeled-dataset`: 把提交清单与标签汇成一份可训练样本集，报出样本量级、时间跨度与正样本比例

### Modified Capabilities

无 —— 本 change 之前 `openspec/specs/` 为空，没有被修改的既有能力。

## Impact

| 项 | 内容 |
|---|---|
| 影响目录 | `data_model/`（新增脚本与产物）、`docs/data-pipeline.md`（回填固定版本、脚本路径与统计数字） |
| 消费的契约 | `docs/contracts/data-fields.md` 表一 `commit`、表二 `commit_label` —— 只读不改 |
| 新增依赖 | `data_model/requirements.txt` 已列 pandas / numpy / GitPython；PySZZ 是否引入视实测结果决定 |
| 下游依赖 | 后端线三张表的建表与灌数、前端三个页面的内容，均等本 change 产出 |
| 数据边界 | 仓库副本、中间产物与样本集一律不入库；只把 `reports/` 下的小体积统计表入库当证据 |
