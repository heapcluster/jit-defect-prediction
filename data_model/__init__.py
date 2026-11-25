"""JIT 缺陷预测内核包。

分层：
- preparation：数据收集、SZZ 打标、清洗与公开数据导入
- pipelines：expert / semantic 两线训练与推理内核
- evaluation：测试集评估、指标与图集

本包与 backend 通过文件契约交换，不在包内直接依赖 Web 框架。
"""
