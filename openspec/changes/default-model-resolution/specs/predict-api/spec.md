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

### Requirement: 同步候选按有效默认模型判断缺行

同步批次 SHALL 在选取候选前固定本批的有效默认模型（同上条解析）。只有存在该模型对应 `(commit_hash, model_name)` 行的提交才能从待预测集合移除；其它模型的行 MUST NOT 代替该默认模型的完成状态。批次上限与 `truncated` 提示保持原语义。本条只保证**有效默认模型**的覆盖，MUST NOT 据此宣称全部在线模型的历史缺口已补齐。

#### Scenario: 仅有非默认模型的行

- **WHEN** 某提交只有非默认模型的预测行，缺少本批有效默认模型的行
- **THEN** 该提交 SHALL 仍进入待预测集合

#### Scenario: 已有默认模型行

- **WHEN** 某提交已存在本批有效默认模型的行
- **THEN** 不因其它在线模型缺行而重新进入该默认覆盖批次

#### Scenario: 截断保序（边界场景）

- **WHEN** 待预测数量超过本批上限
- **THEN** SHALL 保持输入候选顺序并如实置 `truncated`，MUST NOT 把尚未处理的提交标记为完成
