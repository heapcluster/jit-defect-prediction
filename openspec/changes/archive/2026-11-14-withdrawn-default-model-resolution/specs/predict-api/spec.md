## ADDED Requirements

### Requirement: 有效默认模型解析

系统 SHALL 提供全站唯一的「有效默认模型」解析入口，供风险列表、提交详情、趋势、`POST /api/predict` 缺省打分、PR 查询与同步候选判据共同使用，MUST NOT 由读路径与写路径各实现一次。解析顺序 SHALL 为：

1. 注册表冠军（`runtime_setting.champion_model`；未配置时按 design D6 取 `version_key` 最大的已加载模型）在 `prediction` 表有行 → 用冠军；
2. 否则在**已加载模型**中按 `version_key` 降序取第一个有预测行者；
3. 已加载模型都没有预测行 → 用注册表冠军（空库时读写口径一致）。

候选集合 MUST 限于运行时注册表：`prediction` / `model` 表里的历史模型名 MUST NOT 被提升为缺省推理模型。显式传入的 `model_name` 不受本条限制——未加载模型名调用 `POST /api/predict` SHALL 返回 40001，查询接口按该模型读取历史分数仍 SHALL 允许。注册表为空时缺省预测 SHALL 返回 50000 与固定 message，MUST NOT 降级为 40001。

> 口径衔接：本条取代「在线预测入口」中「`model_name` 缺省 SHALL 取注册表中版本序最大模型（`version_key`，design D6）」一句的解析规则。之所以用 ADDED 而不是 MODIFIED 该 Requirement，是因为 change `on-demand-commit-prediction`（状态：进行中，负责人 backend 吕建江）已 MODIFIED 同一 Requirement，两个未归档 change 同时 MODIFIED 会被 `infra/check_spec_references.py deltas` 判为冲突；该 change 归档时须把这句一并对齐到本条。

#### Scenario: 冠军有预测行

- **WHEN** 注册表冠军在 `prediction` 表存在至少一行
- **THEN** 列表、详情、趋势与缺省 `POST /api/predict` 全部使用该冠军，响应回显同一 `model_name`

#### Scenario: 冠军尚无预测行

- **WHEN** 冠军已加载但表内没有任何冠军行，另有已加载模型有行
- **THEN** 各处统一降级到 `version_key` 最大的“有行已加载模型”，MUST NOT 出现读路径降级、写路径仍用冠军的分叉

#### Scenario: 历史高版本模型已卸载（边界场景）

- **WHEN** `prediction` 表存在未加载模型的行，且其 `version_key` 高于全部已加载模型
- **THEN** 缺省解析 MUST NOT 选中该历史模型；缺省预测 SHALL 用注册表冠军成功返回，MUST NOT 因内部选中未加载模型而报 40001

#### Scenario: 注册表为空（边界场景）

- **WHEN** 没有任何已加载模型，且请求未显式指定 `model_name`
- **THEN** `POST /api/predict` SHALL 返回 HTTP 500、code 50000、message 为固定 `internal error`，MUST NOT 回显模型文件路径

#### Scenario: 显式模型名非法

- **WHEN** 请求显式传入不在已加载清单中的 `model_name`
- **THEN** SHALL 返回 40001，message 指出 `model_name` 不在已加载模型清单

### Requirement: 同步候选按在线模型集合判断缺口

同步批次 SHALL 以**当前已加载模型集合**为覆盖目标：某提交只有在集合内每个模型都存在对应 `(commit_hash, model_name)` 行时，才能从待预测集合移除；缺任一模型行 SHALL 仍算待预测。MUST NOT 用「任意模型有行即算完成」或「仅有效默认模型有行即算完成」代替——两者都会让其余在线模型永远补不齐，与 change `realtime-commit-sync` 的全模型落库相反。注册表为空（全部加载失败）时 SHALL 退回有效默认模型单模型判据，MUST NOT 把整批候选当缺口反复重试。批次上限与 `truncated` 提示保持原语义。

#### Scenario: 默认模型已有行但另一在线模型缺行

- **WHEN** 某提交已有有效默认模型的预测行，但缺少集合内另一已加载模型的行
- **THEN** 该提交 SHALL 仍进入待预测集合，由 `predict_commit_all_models` 一次补齐全部在线模型

#### Scenario: 在线模型已覆盖全

- **WHEN** 某提交对集合内每个已加载模型都有预测行
- **THEN** 不进入待预测集合，MUST NOT 重复现算特征

#### Scenario: 注册表为空（边界场景）

- **WHEN** 没有任何已加载模型
- **THEN** 判据 SHALL 退回有效默认模型（同上条解析）单模型口径，MUST NOT 因集合为空而把所有提交判为待预测

#### Scenario: 截断保序（边界场景）

- **WHEN** 待预测数量超过本批上限
- **THEN** SHALL 保持输入候选顺序并如实置 `truncated`，MUST NOT 把尚未处理的提交标记为完成
