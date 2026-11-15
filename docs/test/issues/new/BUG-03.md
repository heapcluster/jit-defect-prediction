# [缺陷][后端] 并发触发同步时第二个请求返回 500 `internal error`，前端只能提示「服务异常」

- 建议级别：**一般**
- 建议 label：`type:bug` `line:backend`
- 被测提交：`2734c1b`（main）
- 发现人：测试方（neon 线自动化执行，2026-11-15）

## 现象

两个客户端同时 `POST /api/sync`，一个 200，另一个 500：

```text
0 500 {"code":50000,"message":"internal error","data":null}
1 200 {"code":0,"message":"ok","data":{"accepted":true}}
```

用户侧表现：连点两次「刷新」，第二次弹「服务异常」，无法判断是"已经在同步"还是服务真挂了，于是继续重试。

## 复现步骤

1. 前置：后端已启动、`SOURCE_REPO` 可用、当前没有同步在跑（`GET /api/sync/status` → `running=false`）。
2. 起两个线程同时打同一个接口：
   ```python
   import httpx, threading
   h = {"X-API-Key": API_TOKEN}
   def call(i):
       r = httpx.post("http://127.0.0.1:8000/api/sync", params={"line": "expert"}, headers=h, timeout=120)
       print(i, r.status_code, r.text[:120])
   ts = [threading.Thread(target=call, args=(i,)) for i in range(2)]
   [t.start() for t in ts]; [t.join() for t in ts]
   ```
3. 频率：必现（其中一个必定 500），代码里由 `_sync_lock` + `running` 判定保证只有一个能进。

## 预期结果

第二个请求应返回**可解释的冲突**：HTTP 409（或既有 `40001` + 明确文案「同步进行中，请稍候」），前端据此把按钮置灰，而不是提示"服务异常"。

## 实际结果

- 第二个请求 `500` + `{"code":50000,"message":"internal error"}`（`backend/app/api/sync.py:286-288` 有意为之）；
- 前端对 5xx 统一按「服务异常」处理，用户看不到"已有同步在跑"这层信息；
- 副作用正确：`sync/status` 未串扰，没有两个 worker 并行改写数据。

## 影响范围

- **接口**：`POST /api/sync` 的冲突分支（并发、重复点击、前端轮询期间二次触发）。
- **前端**：风险列表「刷新」按钮的错误提示语义失真，易引发连续重试。
- **契约**：`docs/api/sync.md` 把「已在同步中」定义为 50000，属用 5xx 表达业务冲突；`openspec/specs/sync-api` 需同步口径。
- **验收影响**：不阻断验收，但影响易用性（T-ST-NF-06）与接口契约一致性（A-18）。

## 建议修复方向（供 owner 参考，测试方不实施）

- 把「已在同步中」改为 409 或 `40001` + 固定文案，前端按该码做禁用态；
- 同步改 `docs/api/sync.md` 与 `sync-api` 规格，保持契约一致；
- 若坚持 5xx，至少把 message 换成可读文案，别用 `internal error`。

## 证据

- 并发用例：`docs/test/integration_test/report.md` T-IN-21（状态不串扰判 PASS，500 本身另记本缺陷）
- 缺陷台账：`docs/test/system_test/bug_list.md` BUG-03
