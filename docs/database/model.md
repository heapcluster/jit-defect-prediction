# model

`实现状态：已实现　期次：一期`

**一句话**：模型注册表，一行对应一个可加载模型；是 `prediction` / `model_figure` / `model_artifact` 的外键目标，也是前端「架构 → 模型」级联选择器的数据源。

实现锚点：backend/app/models.py:36-46

## 字段（逐字对齐 infra/schema.sql）

| 字段 | 类型 | 空值/默认 | 键/索引 | 含义 |
|---|---|---|---|---|
| model_name | VARCHAR(64) | NOT NULL | 主键 | 模型名，全局唯一：`lr_v1` / `lr_semantic_v1` / `lr_fused_v1` / `codebert_e2e_v1` 等 |
| line | VARCHAR(16) | NOT NULL DEFAULT 'expert' | ix_model_line | 所属架构：`expert` / `semantic` / `fused` / `e2e` |
| algo | VARCHAR(64) | 可空 | — | 算法标识：`lr` `rf` `xgb` `lgbm` `et` `svm` `mlp_deep` `tabnet` / `codebert_e2e` |
| version_key | VARCHAR(64) | NOT NULL DEFAULT '' | — | 版本键（同族内排序用） |
| trained_at | DATETIME | 可空 | — | 训练完成时间 |
| feature_version | VARCHAR(32) | 可空 | — | 训练所用特征版本 |

## 主键与约束理由

- 函数依赖只有一组：`model_name → line / algo / version_key`，决定因素是主键，满足 BCNF；`model_name` 是交付契约锁定的自然主键（权重文件名、图目录名都用它），不造代理 id。
- `line` 单列索引：级联选择器按 `line` 分组取数。
- **行由 `model_artifact` 登记派生**（见 [model_artifact.md](model_artifact.md)）：登记 / 更新工件时同事务 upsert 本表行；`model_registry` 只读本表与工件表并校验 checksum，MUST NOT 扫目录形成第二本账。

## 被谁所用

| 方向 | 谁 | 用途 |
|---|---|---|
| 写入 | `model_artifact` 登记派生（训练服务、交付导入） | 注册可加载模型 |
| 读取 | models（清单）、figures（join 取 line）、predict（存在性校验）、默认模型解析 | 级联选择器、图分组、推理定位 |
| 展示 | 风险列表、提交详情、趋势看板、模型性能看板的架构 → 模型级联 | 选架构 → 选模型 |

## 口径

- **模型总量**：expert 8 + semantic 8 + fused 8 + e2e 1 = 25，`model_name` 全部唯一。
- `line` 是显式列，登记时写入，取值一律小写；MUST NOT 从 `model_name` 后缀现场推导。
- 中文显示名不落库：`expert→专家特征`、`semantic→语义`、`fused→融合`、`e2e→端到端` 由 `GET /api/models` 后端常量映射返回。
- **默认模型** = `user_config.default_model`（见 [user_config.md](user_config.md)）；未配置时回退默认规则「expert 线中 `version_key` 最大的已加载模型」。
- 模型加载 / 卸载 / 重载 / 设默认是独立管理能力，不由页面刷新隐式触发；「同步数据」与「刷新模型」是两个操作。
- `retired` 工件对应的行保留但级联选择器过滤为不可选。

## 验收

- 工件登记成功 → 本表行同事务出现；页面无需重启即可在级联中看到新模型。
- 级联按 `line` 列分组，四线 25 模型全部可选（retired 除外）。
- 配置 `default_model` 后默认模型随之变化；清空配置回退版本序规则。