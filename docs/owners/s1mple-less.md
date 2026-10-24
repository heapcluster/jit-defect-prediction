# 吕建江（@s1mple-less）— 后端

> 更新 2026-10-24 ｜ 变更需本人在 PR 里确认 ｜ 上位规则：`docs/repo/collaboration.md`

## 1. 负责范围（有权直接改）

- `backend/**`：`app/`（`api` / `model_registry` / `auth` / `db` / `errors`）、`scripts/`（`seed_dev_data.py`、`security_cases.py`、`perf_loop.py`）
- `backend/.env.example`（模板值必须与 `integration-log.md` §0 一致）
- `backend/scripts/evidence/**`：性能与安全自测证据
- `docs/backend/**`：`api-spec.md`、`implementation.md`、`acceptance.md`
- 联调库结构（SQLite 四张表）与 seed 脚本口径

## 2. 不越界（这些必须找别人）

| 事项 | 找谁 |
|---|---|
| 模型权重、`feature_order.txt`、阈值与解释口径 | 蒋励 |
| 契约三的错误码与性能靶子、字段定义 | 苏哲勋 |
| 前端页面与组件 | 刘帅华 |
| 线上部署形态（MySQL 等） | 苏哲勋（infra） |

## 3. 交付物与验收

- **接口**：契约三 §1 六条路径全部可用，`X-Api-Key` 鉴权 fail-closed（未配置一律拒绝）
- **错误码**：`40001` 参数、`40100` 鉴权、`40400` 不存在、`50000` 内部错误；**不把服务端 message 原文吐给前端**
- **联调库**：`python -m scripts.seed_dev_data` 一条命令建库灌数（3 提交 / 3 特征 / 3 预测）
- **自测**：`security_cases.py` 与 `perf_loop.py` 的每一行结论都必须是脚本真跑出来的，且脚本自己能在假数据上复现

## 4. 原则（做取舍时按这个顺序）

1. **不静默通过。** 检查项不可用、库为空、外部依赖缺失，一律判 FAIL 并让退出码变 1；跳过就等于纵容。
2. **fail closed。** 令牌没配、模型目录缺失这类配置问题，宁可 50000 拒绝，也不许"先跑起来再说"。
3. **不吞异常。** 宽泛捕获必须写明理由并加 `# noqa: BLE001`，且要打印后 `continue`，不许静默 return。
4. **性能结论先拆环节。** 单次耗时拆成 推理 / 解释 / 序列化 三段再下判断（D-14 就是拆完才发现慢在 SHAP 而不是 `predict_proba`）。
5. **证据可复现。** 每个"已验证"都要给命令 + 输出片段；改完的 bug 要补一条不需要外部服务的回归测试。

## 5. 签字权

- `backend/**` 的实现类改动
- 接口实现层与契约不一致时的"实现侧复议"（契约本身仍需苏哲勋改）

## 6. 现阶段待办（滚动）

- `#113`：**未修完**。`security_cases.py` 的 `mask_result` 在 `main()` 声明、在嵌套 `s5()` 里赋值却没有 `nonlocal` → `--mask-url` 静默失效、FAIL 不进 `rc`。修法：加 `nonlocal`，或让 `s5()` 返回第三元组；并补 monkeypatch 回归（500/50000 → PASS 且 rc=0；404/库空 → FAIL 且 rc=1）
- 修完把描述里"修前"的证据替换成真实输出，再推一次触发 CI
