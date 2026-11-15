# [缺陷][后端] `/api/figures` 返回的 6 个图路径没有实体文件，`/static/figures/**` 带正确令牌仍 404，模型性能页图集全裂

- 建议级别：**严重**
- 建议 label：`type:bug` `line:backend` `line:model`
- 被测提交：`2734c1b`（main）
- 发现人：测试方（neon 线自动化执行，2026-11-15）

## 现象

`GET /api/figures?model_name=et_v1` 正常返回 6 条 `figures[]` 与 `file_path`，但按这些路径取图，带正确的 `X-API-Key` 也是 404：

```text
/static/figures/expert/et_v1/roc.png  ->  404
{"detail":"Not Found"}
```

前端「模型性能」页选中模型点「查看」，抽屉里 6 张图全部显示「图片加载失败：404」，浏览器控制台 6 条 404。指标数字（AUC / AP / Accuracy）仍然正常，所以只看数字会误以为页面好的。

## 复现步骤

1. 前置：后端已启动，库内 `model_figure` 有记录（`jit_demo` 由 `data_init.sql` 或同步灌入）；环境变量 `API_TOKEN` 已知。
2. 取元数据：
   ```bash
   curl -s -H "X-API-Key: $API_TOKEN" \
     "http://127.0.0.1:8000/api/figures?model_name=et_v1"
   # data.figures 6 条，file_path 形如 /static/figures/expert/et_v1/roc.png
   ```
3. 取图本体：
   ```bash
   curl -o /dev/null -w "%{http_code}\n" -H "X-API-Key: $API_TOKEN" \
     "http://127.0.0.1:8000/static/figures/expert/et_v1/roc.png"
   # 404
   ```
4. 页面路径：`http://127.0.0.1:5173/model-performance` → 架构选「专家特征」→ 模型选 `et_v1` → 点「查看」。
5. 频率：必现（`backend/static/figures/` 为空时 6/6 失败）。

## 预期结果

- `figures[].file_path` 指向的文件真实存在，带令牌请求返回 `200 image/png`；
- 文件缺失时接口不应返回不可用路径，应给出降级提示（例如 `figures=[]` + `message`），而不是让前端去撞 404。

## 实际结果

- 元数据 6 条齐全，文件 0 个存在；
- 带令牌 404（响应体是 `{"detail":"Not Found"}`，**未走统一错误包络**）；
- 不带令牌同一路径是 401（鉴权中间件工作正常），说明不是鉴权问题，是文件不存在；
- 抽屉 6 张图全裂，控制台 6 条 404。

## 影响范围

- **功能**：模型性能页的核心可视化不可用；四页面里唯一一个「打开就是坏」的页面。
- **数据一致性**：`model_figure` 表记录与磁盘文件不一致，接口把不可用路径当可用返回。
- **环境**：干净检出、容器内、重新生成 `backend/static` 之后都会出现；本机做测试前需人工从 `data_model/pipelines/{line}/reports/figs_by_model/` 拷贝 133 张 PNG 才能正常。
- **验收影响**：直接导致验收 A-06、A-13 不通过，系统测试 T-ST-07 失败。

## 已做的定位（不是修复）

模型线其实已经把图生成到 `data_model/pipelines/{line}/reports/figs_by_model/`（expert 48、semantic 40、fused 40、e2e 5，共 133 张 PNG）。把这些文件手工拷到 `backend/static/figures/` 后，同一路径立刻 `200 image/png`（约 40KB），抽屉 6 张图全部渲染。**结论：代码没问题，缺的是"生成 → 拷到 static"这一步交付流程。**

## 建议修复方向（供 owner 参考，测试方不实施）

1. 把「生成图集 + 拷贝到 `backend/static/figures/`」写进 `README.md` 与镜像构建步骤；
2. 或在 `model_figure` 记录缺失文件时降级：`figures` 只返回实际存在的文件，并在 `data` 里给出 `missing[]`；
3. `/static` 404 走统一错误包络，别把 `{"detail":"Not Found"}` 抛给前端。

## 证据

- 首测截图：`docs/test/system_test/execution_records/model-performance-drawer-404-2026-11-15.png`
- 补齐后复验截图：`docs/test/system_test/execution_records/model-performance-drawer-fixed-2026-11-15.png`
- 接口侧用例：`docs/test/integration_test/report.md` T-IN-29（35 条里唯一失败项）
- 缺陷台账：`docs/test/system_test/bug_list.md` BUG-02
