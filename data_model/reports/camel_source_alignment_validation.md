# Camel 切换补齐验证记录

> 版本：1.0 ｜ 日期：2026-10-15 ｜ 执行：Codex ｜ 审核：待 PR 审核
> 基线：`origin/feat/model/expert-line-training`，提交 `866b7dc`。
> Change：`openspec/changes/camel-source-alignment/`。

## 范围与结论

沿用已有 Camel 固定版本及训练产物，补齐 SZZ 基准登记、报告文案、失败退出、数据源文档和回归测试。本次差异未修改 `backend/`、`frontend/`、训练算法、特征列或时间切分规则；未提交数据集、模型与虚拟环境。

测试与规格校验通过；本机缺少全量 Camel 数据和模型，**没有重跑全量采集、SZZ、8 模型训练或前后端联调**。既有统计来自上游提交，不构成本次独立复现结果。

## 固定版本与证据来源

官方远端核验命令：

```powershell
git ls-remote https://github.com/apache/camel.git refs/tags/camel-4.23.0 'refs/tags/camel-4.23.0^{}'
```

结果：

```text
e7094f7ca2abb03f36d118df0572b569eb28ca4f  refs/tags/camel-4.23.0
b2329103df8f5d1edfca2ad262be09e3be95ee68  refs/tags/camel-4.23.0^{}
```

附注 tag 对象与 peeled commit 不混用。`84461` 条非合并提交来自上游 `data_model/reports/commit_extract_stats.md`；三项外沿 `38716 / 7787 / 6631` 来自同一提交的 `szz_labeling_stats.md`。原报告自检基准未登记，本次仅透明勘误和登记，不追认原运行已通过自检。

## 单元与本地 Git 集成测试

环境：Windows、Python 3.12.14；使用被忽略的 `data_model/.venv`，安装已有声明依赖 pytest、GitPython 和 ruff，未修改依赖清单。

在 `data_model/` 执行：

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe -m pytest -o addopts='' -q -ra
```

最终输出：`67 passed, 1 skipped in 1.60s`。跳过项为 `tests/test_feature_contract.py:118`：干净 checkout 的 `data_model/models` 无被忽略的 `.pkl`。显式清空默认 addopts，仅运行现有测试与本次回归，不将模型文件缺失视为验证成功。

新增测试首先复现了 5 项失败，修正后通过，覆盖：

- CAMEL 编号判据与报告一致，AMQ 编号不进入修复候选。
- 完整提交数或任一外沿未登记时标记「尚未登记、不可比」，不输出 None 或误称子集。
- 输入条数小于或大于完整版本时不可比；条数及判据一致时通过。
- 完整输入判据不符时 CLI 非零退出，禁止继续回溯、写标签或覆盖报告。
- 临时 Git 仓库中真实执行采集与两套 SZZ：生产固定版本不匹配时拒绝输出 CSV；仅在测试内替换固定提交后，验证 `repo_name=camel`、提交时间顺序、父提交关系及缺陷引入回溯。

合成数据和报告只写入测试临时目录，未覆盖既有全量报告。

静态检查（ruff 0.17.0）：

```powershell
.\.venv\Scripts\python.exe -m ruff check tests/test_szz_labeling.py tests/test_camel_source.py
.\.venv\Scripts\python.exe -m ruff check 02_szz_labeling.py --output-format concise
git show 866b7dc:data_model/02_szz_labeling.py | .\.venv\Scripts\python.exe -m ruff check --stdin-filename 02_szz_labeling.py --output-format concise -
```

两个测试文件 `All checks passed!`。脚本检查仍报告 3 条既有规则告警：UP022、UP028、UP017；对基线文件执行相同检查可复现同三项，未新增告警。本次不修改与数据源切换无关的 subprocess、生成器或 datetime 写法，因此**脚本 lint 整体未通过**。

## OpenSpec 与差异检查

使用缓存的 `@fission-ai/openspec@1.11.0`，关闭遥测；本机 npm 包通过 Node 直接执行 npm-cli.js。等价 CLI 调用：

```text
openspec validate camel-source-alignment --strict
openspec validate semantic-feature-mainline --strict
openspec validate public-dataset-quality --strict
openspec validate --specs --strict
```

3 份 change 均显示 valid；活规格结果 `11 passed, 0 failed (11 items)`。另外两份未归档提案同步当前仓库名和样本规模，旧语义特征耗时估算标记为需重测；任务完成状态与范围保持不变。

差异核对使用 `git diff --check` 和 `git diff --name-only 866b7dc -- backend frontend`：无空白错误，前后端差异为空。归档、历史实验数字及原始图示提示词保留来源，不将旧 ActiveMQ 证据改写成 Camel 实测。

## 已知缺口

- 需要具备完整数据和训练环境后，按 `docs/model/data-pipeline.md` §5 独立复现全量结果；本次未完成该验收。
- 本次不验证模型文件内部特征契约、模型服务加载、前后端联调或全量运行性能。
- SZZ 脚本存在上述 3 条基线 lint 告警，未在本次范围内清理。
- 自检条数与外沿相符不等于验证输入来源；仍须核对固定提交并使用相应采集产物。

## 变更日志

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-10-15 | 1.0 | 记录 Camel 补齐测试、固定版本核验及未执行的全量验收 |
