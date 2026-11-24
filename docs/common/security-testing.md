# 安全性测试

> 来源：`docs/common/安全性测试.pdf`（共 5 页）
> 说明：保留全部文字与表格；原 PDF 中的截图、示意图未纳入。

专业课综合实训III 安全性测试 童浩楠 hntong@bjtu.edu.cn 软件学院

## 重构期验收口径（重构期追加，不改原文）

`实现状态：口径已发布；新增能力测试待新增` `期次：一期`

- 本文原文为课程方法论讲义转录（来源 PDF），**不含本系统实测数字、证据路径与执行记录**；原文全部保留不动。历史基准数字（如上游 `866b7dc` 报告外沿基准）登记于 [database/README.md §3](../database/README.md)，不得删改。
- 重构后验收口径按新契约扩展，覆盖六个新增能力面；**对应测试一律标「待新增」，尚未在本机生成/执行**：
  1. 配置持久化与重启恢复（`user_config`，[database/README.md §6](../database/README.md)、[database/user_config.md](../database/user_config.md)）——未实现；
  2. 任务五态：排队中 / 运行中 / 成功 / 失败 / 已取消（`job` 表，database/README.md §7）——未实现；
  3. 数据集导出 CSV / XLSX（database/README.md §2）——未实现；
  4. 在线性能评估：阈值 / 指标配置、多模型对比（[function_point/model_performance.md](../function_point/model_performance.md)）——部分（展示层已实现，在线重算未实现）；
  5. XAI 技术选择与解释兼容矩阵（`TODO/07`、[database/algorithm.md](../database/algorithm.md) family 单源）——未实现；
  6. 源码浏览与缺陷定位（`TODO/08`）——未实现。
- **安全测试待新增面**（对应新契约安全条款）：收集任务仓库路径限定在配置允许根目录内、URL 仅 https/git 协议白名单、MUST NOT 把用户输入拼进 shell 字符串（database/README.md §1）；`X-API-Key` 统一鉴权、`/static/**` 不免鉴权（§8 不变量 6）；API Key / 口令等敏感信息 MUST NOT 入库（§0）；`user_config` 越权访问 / 未知键 / 非法值返回明确错误码（§6）；源码浏览路径穿越与读取边界（TODO/08）。全部待新增，尚未在本机执行；本文不写入任何密钥 / 口令实值。
- 旧口径 → 新契约映射（下列旧口径句**未出现在本文原文中**，本表供重构期验收引用，防止沿用其他历史文档的旧口径；现状实现仍为旧口径，状态如表注）：

| 旧口径句 | 新契约指向 | 现状实现状态 |
|---|---|---|
| 「阈值写死 .env」 | 唯一权威 `user_config`，`.env` / pipeline 常量降级为出厂默认（database/README.md §6、database/user_config.md） | 未实现配置化：三处各自为政（`backend/app/config.py:131-133`、`frontend/src/utils/thresholds.js:3`、`data_model/pipelines/*/config.py`） |
| 「五张表即最终设计」 | 12 表清单与分期（database/README.md §0） | 现库仍为五张表，新表未实现 |
| 「仅 expert 有 SHAP」 | 按算法族兼容矩阵选择解释器、XAI 技术可配置（TODO/07、database/algorithm.md） | 仍旧口径：SHAP 只对 expert 线计算（`backend/app/services/predict.py:278-280`） |
| 「同步是唯一计算入口」 | sync 拆为收集与批量预测；评估 / 训练 / 解释各有独立入口（database/README.md §7、function_point/model_performance.md §2） | 仍旧口径：`backend/app/api/sync.py:8` 自认唯一入口，状态为进程内存 |

## 安全性测试分类

- 安全性缺陷——漏洞
    - 脆弱性（vulnerability），又称弱点或漏洞，是IT系统中存在的可能被威胁利用造成损害的薄弱环节，脆弱性一旦被威胁成功利用就可能违犯安全策略, 对IT系统（资产）造成损害。
- 安全性测试
    - 安全性测试（Security Testing）是为了发现系统潜在的安全漏洞、确认系统能够保护数据免遭攻击、确保软件的访问授权功能正常运行的一系列测试活动。 其核心目标在于识别出系统的弱点、防御能力和确定外部威胁可能对系统造成的损害。
- 安全性测试
- 安全功能测试VS安全漏洞测试

 安全功能测试 (Security Functional Testing)：数据机密性、完整性、可用性、不可否认性、身份认证、授权、访问控制、审计跟踪、委托、隐私保护、安全管理等。

 安全漏洞测试 (Security Vulnerability Testing)：从攻击者的角度,以发现软件的安全漏洞为目的。安全漏洞是指系统在设计、实现、操作、管理上存在的可被利用的缺陷或弱点。比如注入类（SQL注入、命令注入等）、业务逻辑漏洞、访问控制类（水平/垂直越权、未授权访问等）等等
