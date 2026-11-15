# [缺陷][文档] `README.md` 称 `GET /api/health` 是「公开的」，实际三条健康探针都要求 `X-API-Key`

- 建议级别：**轻微**
- 建议 label：`type:docs` `line:docs`
- 被测提交：`2734c1b`（main）
- 发现人：测试方（neon 线自动化执行，2026-11-15）

## 现象

按 `README.md` §二 第 5 步「先查公开的 `GET /api/health`」执行，不带请求头拿到 401：

```text
GET /api/health  ->  401 {"code":40100,"message":"missing or invalid token","data":null}
```

而 `docs/api/health.md:20` 写的是「三条都需要 `X-API-Key`（实测不带 token 返回 `401 / 40100`）」，与实现一致。**是 README 写反了，不是代码问题。**

## 复现步骤

1. 前置：后端已启动，`API_TOKEN` 已配置。
2. 执行：
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/health
   # 401
   curl -s -o /dev/null -w "%{http_code}\n" -H "X-API-Key: $API_TOKEN" http://127.0.0.1:8000/api/health
   # 200
   ```
3. 频率：必现。

## 预期结果

README 与实际行为一致：要么写清「三条健康探针都需要 `X-API-Key`」，要么把探针改成免鉴权（需同步 `docs/api/health.md` 与安全用例）。

## 实际结果

README §二 第 5 步与 §一 自检示例的表述不一致（§一 的 curl 带了 header，§二 说"公开的"），照 §二 做会 401。

## 影响范围

- **文档**：新同学按 README 起步即失败，容易误判"服务没起来"。
- **测试**：脚本以 `/api/health/live` 做探活时必须带 header，早期脚本曾因此误报。
- **验收影响**：A-17（按部署说明从零复现）不通过的原因之一。

## 建议修复方向

改 README 一句话即可：

```diff
- 5. **走通链路**：先查公开的 `GET /api/health`，再带 `X-API-Key: <本机 API_TOKEN>` 查 `GET /api/models`；
+ 5. **走通链路**：先带 `X-API-Key: <本机 API_TOKEN>` 查 `GET /api/health`，再查 `GET /api/models`；
```

## 证据

- 缺陷台账：`docs/test/system_test/bug_list.md` BUG-05
- 契约正文：`docs/api/health.md` §权限
