## 1. 提案交付

- [x] 1.1 本提案自 `docs/spec/nfr-evidence-scripts` 提 PR 至 `main`，描述写清四件事并关联本 change id；审阅人苏哲勋
      —— **PR #32 已合入**（2026-09-20，d8a5846，审阅人苏哲勋）；两轮评审意见均已修正（4c06bc0 创建日期+显式风险节；e473a36 契约引用 1.3→1.4、Sprint 0 截止 9/25→10/02）

## 2. 脚本实现

- [x] 2.1 `backend/scripts/perf_loop.py`：100 次请求、p50/p95/p99/最大值、达标判定；BASE_URL/API_TOKEN 走环境变量；服务不可达非零退出
      —— 完成：分位数口径升序第 ceil(q*n) 位（design D4）；服务不可达退出码 1、缺 API_TOKEN 退出码 2；独立 httpx 客户端、不 import 应用代码（design D2）
- [x] 2.2 `backend/scripts/security_cases.py`：两组用例 + 50000 掩码断言；逐用例 PASS/FAIL 与汇总；断言失败非零退出
      —— 完成：S1–S5（缺失/错误令牌、size=101、granularity=day、hash 39 位）+ 响应泄露扫描（堆栈/SQL/路径关键词零命中）
- [x] 2.3 两脚本对本地 feat 服务自测跑通（安全组不依赖模型；性能组用占位模型）
      —— 完成：2026-09-19 占位模型自测跑通（p95=33.8ms）；2026-09-20 真模型复跑（p95=21.6ms），见 3.2 / 4.3 证据

## 3. 证据产出（占位阶段）

- [x] 3.1 安全组证据 md 进仓库（标注构建来源 = #30 head 等价本地构建）
      —— 完成：`backend/scripts/evidence/security-2026-09-19.md`（全 PASS）
- [x] 3.2 性能组占位模型证据 md 进仓库（显式标注「占位模型（待真 .pkl 重跑）」）
      —— 完成：`backend/scripts/evidence/perf-placeholder-2026-09-19.md`（p50 31.2 / p95 33.8 / p99 36.0 / max 7233.6ms，模型 tree_placeholder_v0）

## 4. 交付与后续重跑

- [ ] 4.1 实现 PR（脚本 + 占位证据）自 `feat/backend/nfr-evidence-scripts` 提至 `main`；审阅人苏哲勋
- [x] 4.2 #30 合入后对 main 服务复跑安全组，追加证据 md（change 更新提交）
      —— 2026-09-20 完成：对 main@2cf0ce9 等价本地构建复跑（其后 #44/#45 均为纯文档改动，应用代码一致），`security-2026-09-20.md` 全 PASS
- [ ] 4.3 真 `.pkl` 交付后重跑性能组，追加真模型证据 md；回填飞书《产品需求文档》第七章性能/安全实测结果（9/23 截止）
- [ ] 4.4 回飞书看板更新任务 10 状态与关联链接
