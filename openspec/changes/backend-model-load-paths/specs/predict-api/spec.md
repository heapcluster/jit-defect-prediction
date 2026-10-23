## ADDED Requirements

### Requirement: 仓库模型模块可导入与加载失败汇总

加载注册表前，后端 SHALL 将仓库根下 `data_model/` 的绝对路径加入模块搜索路径，使按 `pipelines.*` 可导入类路径序列化的可信交付模型能够被解析；同一绝对路径 MUST NOT 因重复加载而重复插入。该路径 SHALL 由仓库位置确定，MUST NOT 由 HTTP 请求或外部权重目录决定。加载完成 SHALL 保留成功模型清单；当反序列化失败或特征宽度不符时，SHALL 将失败模型名汇总为 ERROR 级服务端日志，保留失败详情，继续加载其它有效模型。加载失败 SHALL NOT 阻断服务启动，HTTP 响应 MUST NOT 包含异常堆栈或本地路径。

#### Scenario: 规范包路径模型从后端工作目录加载

- **WHEN** 工作目录为 `backend/`，可信交付模型使用存在于仓库的 `pipelines.*` 类路径保存，依赖完整且特征宽度符合契约
- **THEN** 无需手工设置 PYTHONPATH 即能加载该模型，注册表与成功日志包含其模型名

#### Scenario: 多次加载不重复修改搜索路径

- **WHEN** 同一进程连续执行两次模型加载
- **THEN** `data_model/` 绝对路径在 `sys.path` 中仅出现一次，注册表仍按当前模型文件重新建立

#### Scenario: 损坏文件不阻断有效模型

- **WHEN** 目录同时包含有效模型与无法反序列化的 `.pkl`
- **THEN** 有效模型保持可用，损坏模型不进入注册表，ERROR 汇总包含失败模型名，原始异常只写服务端日志

#### Scenario: 特征宽度不符纳入失败汇总

- **WHEN** 某模型声明的输入特征宽度不等于契约二规定的 14 项
- **THEN** 保留现有拒收行为，并在本次 ERROR 汇总中列出该模型名，MUST NOT 为加载成功而跳过宽度自检

#### Scenario: 所有候选模型加载成功

- **WHEN** MODEL_DIR 内所有候选模型都能解析且特征宽度合法
- **THEN** 输出成功清单，MUST NOT 输出虚假的失败模型 ERROR 汇总

#### Scenario: 非可导入主模块类保持真实失败

- **WHEN** 权重依赖 `__main__.TabNetWithEarlyStop`，而当前入口没有该类
- **THEN** 将该权重报告为加载失败，不用路径添加伪称成功，不修改全局 `__main__` 来掩盖权重导出问题

#### Scenario: 加载异常不泄露到 HTTP

- **WHEN** 某模型加载异常后客户端请求预测
- **THEN** 继续使用现行 `docs/backend/api-spec.md` 的响应包络和错误语义，响应不包含权重路径、模块堆栈或失败清单详情
