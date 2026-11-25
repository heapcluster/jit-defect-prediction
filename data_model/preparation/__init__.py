"""数据准备层：collect / clean / public_load 三个入口。

01_* ~ 05_* 为 collect 内部的阶段实现，编号体现流水线顺序，由 collect.py 统一编排；
外部调用请走 collect.run / clean.run / public_load.load_public。
"""
