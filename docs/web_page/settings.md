# 设置页（Settings）

实现状态：部分　期次：一期

W1 配置区已接线于 `/storage`：元数据驱动表单、批量保存、单键恢复默认与读取失败重试。非空清洗/训练模板及 LIME 等选项随 W4/W5/W8 完善；八功能 tab 的完整导航编排在 W10 实现。

## 一句话

以 `user_config` 为唯一配置源，集中编辑全局键与各模块命名空间键，经 `/api/config` 族原子保存、立即生效并在后端、容器或进程重启后恢复；`.env` 仅提供出厂默认值，不在本页编辑。

## 入口与导航

- 功能①（数据库存储）tab 内用户配置区页内子视图（子签）；`/settings` 重定向到 `/storage` 并选中本配置区，入口索引见 [README.md](README.md)。
- 字段与值类型见 [../database/user_config.md](../database/user_config.md)，接口见 [../api/config.md](../api/config.md)；模块默认值由对应工具台读取。
- 模型、数据集、XAI 与指标选项分别来自 `/api/models`、`/api/datasets`、`/api/explain/techniques`、`/api/evaluate/metrics`，前端不写死清单。

## 线框图

```
┌─ 设置（唯一配置源：user_config）────────────────────────────────────────┐
│ [全局] [Collect] [Clean] [Train] [Predict] [Explain] [Localization]     │
│ ┌─ 全局 ─────────────────────────────────────────────────────────────┐ │
│ │ decision_threshold[0.5]  risk_high_threshold[0.5]  risk_mid[0.2]   │ │
│ │ 校验：0 < risk_mid_threshold < risk_high_threshold < 1              │ │
│ │ default_model[▾] default_dataset[▾] default_xai[▾]                 │ │
│ │ metrics_selected[☑auc ☑ap ☑f1 ☑precision ☑recall ☑accuracy …]     │ │
│ │ primary_metric[▾ auc]  effort_enabled[☑]                           │ │
│ │ page_prefs：每页条数[20▾] 抽屉展开态[☑记住]（白名单对象）           │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│ ┌─ 模块命名空间（随页签显示，全部保存到 user_config）─────────────────┐ │
│ │ collect.allow_roots[路径列表] collect.protocol_whitelist[https,git] │ │
│ │ clean.chain_templates[处理链模板编辑器] train.templates[训练模板]   │ │
│ │ predict.batch_size[100] cache_ttl[3600s] retry_max[3]              │ │
│ │ explain.cache_ttl[3600s] compare_enabled[☑]                        │ │
│ │ localization.weights[权重对象] top_n[5文件/30行]                   │ │
│ │ localization.file_size_max[______bytes]                            │ │
│ │ localization.suggestion_sources[☑模板 ☑LLM ☑历史修复]              │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│ 当前来源[user/global/factory]  [保存] [恢复默认▾ 单键/当前组]           │
│ 保存即生效；异常关闭或重启后自动恢复。                                  │
│ .env 仅出厂默认；API Key/密码/LLM Key 不在本页出现、不入库。            │
└────────────────────────────────────────────────────────────────────────┘
```

图中数值均为占位示意。`decision_threshold` 属于新预测/评估运行的判定配置，`risk_high_threshold` 与 `risk_mid_threshold` 属于展示分档与趋势高风险口径，三者分区说明。

## 控件与接口映射

| 控件 | 端点 | 配置键与校验 |
|---|---|---|
| 页面加载 | `GET /api/config` | 返回全部生效键、value_type、source=user/global/factory、updated_at |
| 判定 / 风险阈值 | `PUT /api/config/{key}` 或批量 `PUT /api/config` | `decision_threshold`、`risk_high_threshold`、`risk_mid_threshold`；均为 (0,1)，且 mid < high |
| 默认模型 | 选项 `GET /api/models`；写 `/api/config` | `default_model`；须为已登记 model_name |
| 默认数据集 | 选项 `GET /api/datasets`；写 `/api/config` | `default_dataset`；须为已登记 dataset_id |
| 默认 XAI | 选项 `GET /api/explain/techniques`；写 `/api/config` | `default_xai`；须为注册技术 |
| 指标多选 / 主排序 | 选项 `GET /api/evaluate/metrics`；写 `/api/config` | `metrics_selected` list；`primary_metric` 必须属于该集合 |
| effort 开关 | `PUT /api/config/{key}` | `effort_enabled` bool |
| 页面偏好 | `PUT /api/config` | `page_prefs` object；仅允许页大小、抽屉展开态等白名单子键 |
| 收集路径 / 协议 | `PUT /api/config` | `collect.allow_roots` object/list 按键 schema；`collect.protocol_whitelist` 仅 https/git 等登记协议 |
| 清洗模板 | `PUT /api/config` | `clean.chain_templates` object；步骤、顺序与参数经操作注册表校验 |
| 训练模板 | `PUT /api/config` | `train.templates` object；算法、超参、划分与种子经算法库 schema 校验 |
| 预测运行参数 | `PUT /api/config` | `predict.batch_size` 正整数；`predict.cache_ttl` 非负秒数；`predict.retry_max` 非负整数 |
| 解释运行参数 | `PUT /api/config` | `explain.cache_ttl` 非负秒数；`explain.compare_enabled` bool |
| 定位权重 / Top-N | `PUT /api/config` | `localization.weights` object；`localization.top_n` object，文件数与行数为正整数 |
| 定位文件 / 建议 | `PUT /api/config` | `localization.file_size_max` 正整数字节数；`localization.suggestion_sources` list，仅模板/LLM/历史修复 |
| [保存] | `PUT /api/config`（items[] 批量） | 任一键非法则整批不写；成功返回最新生效项 |
| 单键保存 | `PUT /api/config/{key}` | 用于明确单键编辑；同样执行类型与跨键校验 |
| [恢复默认] | `DELETE /api/config/{key}` | 删除当前用户键并回退 global/factory；显示回退后的值与来源 |

## 配置生效边界

- 风险高/中阈值保存后，风险列表与详情重新分档，趋势重新查询高风险计数；不改写已存 risk_score。
- `decision_threshold` 供之后发起的预测与评估运行使用；已交付文件及既有预测记录不被页面批量改写。
- 默认模型、数据集与 XAI 改变后续页面的缺省选择；用户已显式选择的当前对象不被强制替换。
- `metrics_selected / primary_metric / effort_enabled` 作为评估工具下一次显式运行的默认值；历史输出仍按各自 manifest 展示。
- 模块命名空间键在对应工具台 [运行] 时形成配置快照并写入 manifest；页面运行中的任务继续使用原快照。

## 交互流程

1. 进入页面调用 `GET /api/config`，按全局与模块页签回填全部控件，并显示每项来源 user/global/factory。没有用户键是正常状态，不是加载失败。
2. 并行获取模型、数据集、XAI 和指标选项；某组选项失败只禁用对应控件并给重试，其他配置仍可查看。
3. 编辑时执行即时提示：数值类型与范围、mid < high、主指标属于勾选集合、命名空间对象 schema、路径与协议白名单。最终裁定由后端完成。
4. [保存] 将本次修改组成 items[] 调 `PUT /api/config`。任一键非法则整批 40001、原值不变；成功后以响应重新回填，不使用未经确认的本地值冒充已保存。
5. 保存成功后按「配置生效边界」刷新相关只读展示或让后续工具运行读取新值。运行中的 job 不被修改，已下载文件不被重写。
6. [恢复默认] 对选定键调用 `DELETE /api/config/{key}`，显示 fallback_source 与回退值；不得把出厂值重新写为用户键。
7. 后端、容器或进程异常关闭后重启，再次进入页面仍由 `GET /api/config` 返回已保存值；所有页签均须通过同一恢复验收。
8. 本页不提供 `.env` 文本框，不展示或提交 API Key、数据库密码、LLM Key。服务端配置中的密钥引用也不得作为值入库。

## 空态与错误

- 加载中显示分组骨架；无用户配置时显示 factory/global 生效值与来源；读取失败显示错误和 [重试]，不得把空响应当成全默认。
- 未知键、值类型错误、阈值越界、mid ≥ high、主指标未勾选、非法命名空间对象或敏感键均返回 40001，整批原值不变。
- default_model/default_dataset 指向不存在登记对象时返回 40400，已登记但不可用或未注册的 default_xai 返回 40001，均保留原配置；选项已下线时显示失效原因，不静默换成别项。
- DELETE 用户行不存在的键返回 40400；40100 禁用保存与恢复默认；50000 显示内部错误并保留未提交编辑草稿。
- 配置写入成功但某展示页刷新失败时，配置仍视为已保存；对应页面独立显示重试，不回滚 user_config。

## 验收

- 全局十键 decision_threshold/risk_high_threshold/risk_mid_threshold/default_model/default_dataset/default_xai/metrics_selected/primary_metric/effort_enabled/page_prefs 全部可读写并按来源回显。
- 所有指定模块键均可编辑：collect.allow_roots/protocol_whitelist、clean.chain_templates、train.templates、predict.batch_size/cache_ttl/retry_max、explain.cache_ttl/compare_enabled、localization.weights/top_n/file_size_max/suggestion_sources。
- 阈值跨键约束、指标集合、默认对象存在性和各命名空间值类型均由后端校验；批量中任一非法则整批不写。
- 风险阈值保存后展示页联动；decision_threshold 与指标设置用于后续显式运行，不改写历史文件或任务快照。
- 恢复默认通过 DELETE 回退 global/factory，来源标注正确；默认模型、数据集、XAI 与指标选项均来自接口。
- 保存一组全局键和每个模块至少一个命名空间键，重启后端、容器及异常关闭恢复场景后值均保持。
- `.env` 不可在本页编辑，页面、接口响应与数据库均不出现 API Key、密码、LLM Key 等敏感信息。
