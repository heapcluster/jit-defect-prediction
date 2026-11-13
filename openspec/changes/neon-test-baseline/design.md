# neon-test-baseline — 设计决策

## 1 · 端点清单用源码静态对照，不用 `/openapi.json`

**取舍**：本机没有可用的后端运行时（系统 Python 为 WindowsApps 占位程序；conda base 与 moonlit_venv 均缺 `sqlalchemy`，无法 `import app.main`）。运行时契约是权威分母，但拿不到。

**决定**：以 `backend/app/api/*.py` 的路由声明 + `docs/api/*.md` 的字段口径做静态对照，并在文档标题行显式写「未取得运行时 `/openapi.json`，不是通过证据」。

**理由**：静态清单能覆盖「分母是否完整」「用例设计是否可落地」两件事，且不会对读者产生「已联调」的误导；反之，为了拿到运行时契约去装依赖，违反本轮「不得安装环境」的约束。代价是与 2.3 万提交版本的实际序列化细节可能漂移，因此清单里把已知易漂移点（`features:null`、多余请求体、`started_at` 无 `Z`）单列出来。

**替代方案与否决原因**：
- 用 Postman Collection 直连远端服务：本机无部署实例，且远端不可假定存在。
- 用 `frontend/tests/*` 的 mock 响应反推清单：mock 是前端作者写的断言，不是服务端事实，会形成循环取证。

## 2 · 集成用例放进 `backend/scripts/`，不进 `backend/tests/`

**取舍**：仓库 CI 会真实执行 `backend/tests`（依赖 MySQL 服务与固定夹具），而集成用例需要一台**已启动的服务**与真实数据。

**决定**：集成用例实现为 `backend/scripts/integration_cases.py`，用 `httpx` 打运行中的 `BASE_URL`；`perf_loop.py`、`security_cases.py` 同理。三者都不进 `pytest` 收集（`pytest.ini` 的 `testpaths=tests`）。

**理由**：把「需要活服务的黑盒用例」塞进单测目录会让 CI 必须额外起进程与随机端口，失败原因（服务没起 vs 断言写错）混在一起；脚本形态可本地随时复跑、可传 `BASE_URL` 指向预发环境，也贴近课程「接口测试脚本」的交付口径。

**修订记录**：2026-11-10 初版曾决定「不写任何可执行用例」，理由是当时本机无可用 Python 运行时、无法收集验证。2026-11-12 用户提供了 conda 环境后该前提消失，脚本已实跑（35/35、12/12、perf 达标），原决定随之撤销；保留此条以说明为何前后不一致。

## 3 · 执行记录独立成文，不改 `docs/test/integration_test/report.md` 的结论列

**决定**：`docs/test/system_test/execution_records/neon-test-execution.md` 记录本轮执行边界；`docs/test/integration_test/report.md` 只追加一段「本轮未执行 + 指向执行记录」的说明，不填任何「通过」。

**理由**：`docs/test/integration_test/report.md` 是**证据索引**，其表格列写的是「结果 / 证据链接」，一旦把「环境受限」写进结果列，后续读者容易把索引里的文字当结论。索引保持原样、只补口径说明，能把「未执行」与「已执行」的边界留在独立文档里，便于按提交号追证据。

## 4 · 口径偏差只登记、不改契约

**决定**：6 处文档与代码不一致（D-01~D-06）写入清单 §3 与 `test-evidence` 规格，不直接修改 `docs/api/*.md`。

**理由**：`docs/overview.md` 明确 `docs/` 是权威真源、AI 不得擅自改动；且这 6 处里 D-03（多余字段静默忽略）、D-06（`started_at` 时区）属**代码侧**问题，改文档会把真实缺陷抹平。正确处理是先由 neon 登记 Issue，再由负责人裁定是改代码还是改契约。

## 5 · 新增 `test-evidence` 能力而不是复用 `nfr-evidence`

**理由**：`nfr-evidence` 管的是性能 / 安全脚本与 evidence 文件，范围是「跑出数」；本轮要固化的是「清单从哪来、执行记录怎么写、拿不到环境时怎么写」的**取证纪律**。两者受众相同但可校验对象不同，混写会让 `nfr-evidence` 的 Scenario 失焦。

## 6 · 风险与回退

- 静态清单与运行时漂移 → 环境就绪后第一步跑 `/openapi.json` 比对并回填，漂移处按运行时改。
- 读者把用例设计表当已执行 → 表格「状态」列统一写「未执行」，§5 明确「实测接口覆盖率 0/11」。
- 回退方式：本 change 只新增文档，`git revert` 单个提交即可完全回退，不影响构建与既有测试。
