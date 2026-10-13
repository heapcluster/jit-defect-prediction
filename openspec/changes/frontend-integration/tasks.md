## 1. 页面实现

- [x] 1.1 风险列表页 `RiskList.vue`：筛选（model_name / min_risk / 时间范围）+ 表格 + 分页 + 点击行跳详情
- [x] 1.2 提交详情页 `CommitDetail.vue`：风险值 + 风险等级标签 + 14 项特征（五维分组）+ explanation 解释条
- [x] 1.3 趋势看板页 `TrendBoard.vue`：粒度切换 + 折线图 + 汇总卡片 + 明细表
- [x] 1.4 ECharts 折线图封装到 `components/`，不在页面里散写

## 2. 三态与错误码

- [x] 2.1 三态齐全：加载中 / 空数据 / 请求失败（空数据不是错误）
- [x] 2.2 错误码按 `docs/frontend/pages.md` 第 5 节区分处理（40001 / 40100 / 40400 / 50000）

## 3. 字段核对

- [x] 3.1 每页字段名与 `docs/frontend/pages.md` 映射表逐字一致，不改名、不驼峰
- [x] 3.2 风险值由前端 ×100 转百分比；概率字段取 0~1 小数不转字符串

## 4. 联调与交付

- [x] 4.1 三页面对接 API-01/02/03，留联调记录
- [ ] 4.2 提交 PR 并写明关联 change id `frontend-integration`，由非作者审阅合入
- [ ] 4.3 回飞书看板更新任务状态

## 5. 测试与验证

### 5.1 场景覆盖矩阵

| 场景 | 风险列表 | 提交详情 | 趋势看板 |
|---|---|---|---|
| 加载中 | ✅ 骨架屏 | ✅ 骨架屏 | ✅ loading 占位 |
| 空数据 | ✅ 提示+清空筛选 | ✅ 空态 | ✅ 提示+重置范围 |
| 请求失败 | ✅ 按错误码 | ✅ 按错误码 | ✅ 按错误码 |
| 40001 参数非法 | ✅ 指出参数 | — | ✅ 指出参数 |
| 40100 未鉴权 | ✅ 不重试 | ✅ 不重试 | ✅ 不重试 |
| 40400 不存在 | — | ✅ 返回列表 | — |
| 50000 服务错误 | ✅ 重试 | ✅ 重试 | ✅ 重试 |
| 未预测提交（risk_score=null） | — | ✅ 显示「尚未预测」 | — |

边界 / 异常场景：

| 场景 | 覆盖 |
|---|---|
| 同路由 query 改变（下钻跳转带回新日期） | ✅ 风险列表 watch(route.query) 重查 |
| 同路由 query 移除 | ✅ 清日期 + 重置分页 + 重查 |
| 日期末秒（end 纯日期含当天） | ✅ 前端送纯日期，依赖 #62 服务端含结束日全天 |
| 粒度切换不查询就下钻 | ✅ 下钻用 loadedGranularity（已加载粒度） |
| 并发乱序响应 | ✅ requestId 防过期，粒度与 series 一起提交 |

### 5.2 验证清单

- [x] 5.2.1 `npm run build` 通过 —— 判据：exit 0 且输出 `✓ built`
- [x] 5.2.2 `npm run lint` 0 error —— 判据：exit 0 且无 error / warning
- [x] 5.2.3 `openspec validate --changes frontend-integration` 通过 —— 判据：显示 valid
- [x] 5.2.4 前后端联调 —— 判据：带 `X-API-Key` 请求 `GET /api/commits` 返回 `code=0` 且有 `items`；无 key 返回 401

### 5.3 执行证据

| 项 | 证据 |
|---|---|
| 提交 | 粒度快照 `d6bc0f4`（业务实现 `94b43b3`；格式 `cbc9f6b`；并发 `77d5e83`） |
| 环境 | Windows 11，Node 24，Python 3.12；cwd=backend 执行 `python -m scripts.seed_dev_data` 生成 SQLite 种子（3 提交/3 特征/3 预测） |
| 命令 | `npm run build` / `npm run lint` / `openspec validate --changes frontend-integration` |
| 结果 | build ✓（<1s）；lint 0 error 0 warning；openspec validate 通过 |
| 联调证据 | `GET /api/commits?page=1&size=3`（`X-API-Key: dev-token-*`）→ `{"code":0,...,"items":[...3 条]}`；无 key → HTTP 401；详情 `GET /api/commits/{hash}`、趋势 `GET /api/trends` 同链路可达 |

### 5.4 阻断 / 不适用说明

- **阻断**：#62（时间范围闭区间语义）未合入，前端送纯日期依赖 #62 落地；#60 按「#62 先合、#60 后合」排期。
- **不适用**：`POST /api/predict` 无页面依赖，不纳入本 change 页面测试范围。

### 5.5 落地结论

F2/F3 已落地（三页面 + 提案 + 规格）；F4 联调已打通本地前后端链路（三页均拉到真实数据）。待 #62 合入后 #60 复审合并，正式联调记录补入 `docs/frontend/`（不使用已迁移的 docs/implementation/ 路径）。
