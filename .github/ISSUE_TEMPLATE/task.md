---
name: 任务
about: 一件可验收的事（一个交付物或一个功能点）。标题格式「[线] 做什么」
title: "[线] "
labels: ""
assignees: ""
---

<!--
新建前先看：一个 Issue = 一件可验收的事，不是「今天干了什么」。
标签在仓库里需先创建，命名见 docs/collaboration.md 第 5 节：
  type:feat / type:bug / type:docs / type:test
  line:model / line:backend / line:frontend / line:infra / line:docs
  sprint:0 / sprint:1 …
-->

## 要做成什么

<!-- 一句话说清做完之后是什么样子 -->

## 验收标准

<!-- 可检查、可出示证据。写「接口能返回 200」而不是「接口正常工作」 -->

1.
2.

## 归属

| 项 | 值 |
|---|---|
| 线 | `line:` |
| Sprint | `sprint:` |
| 负责人 | |
| 关联 OpenSpec change | |
| 对应飞书看板行 | |

## 交付物

<!-- 具体产物：文件、脚本、文档、接口。不是「完成开发」 -->

## 依赖与阻塞

<!-- 依赖谁先完成？卡住了找谁？没有就写「无」 -->

## 完成判定

四条同时满足才算做完（见 `docs/sprint0-scope.md` 第 5 节）：

- [ ] 本地能跑，且别人按文档也能跑出同样结果
- [ ] 有验证证据（命令输出 / 截图 / 测试结果）
- [ ] 规格或契约已同步
- [ ] PR 已由非作者审阅并合入 `main`
