# 撤回说明

状态：**已撤回，未按本 change 的 delta 合并到活规格**。原 proposal、design、tasks 和 specs 保留为历史记录；旧勾选与证据仅反映当时的实施，不能作为当前验收结论。

原因：冠军热切换、单冠军同步和旧 webhook/PR 入口不再符合当前 API 与数据口径，见 `docs/api/`。

后续实施必须以现行 `openspec/specs/` 与 `docs/` 为基线新提 change，经评审和实测后归档。本次只退出活跃队列，不修改产品代码。
