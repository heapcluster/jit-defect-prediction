# 修缺陷提交识别抽样复核（tasks.md 3.7）

> 判据 D4 = 含缺陷编号 `AMQ-<数字>` **且** 含修复语义 `fix`/`bug`/`patch`（词首边界 `\b`，故 `dispatch`/`debug`/`prefix` 不算），见 `docs/data-pipeline.md` 第 7 节

> 抽样方式：按 `committed_at` 排序后**固定步长**各取 30 条。用步长而非随机数，是为了同一份输入每次产出同一份名单，便于他人复算。

| 输入 | 值 |
|---|---|
| 提交清单 | 11050 条 |
| 判为修缺陷提交 | 2417 条 |
| 未判为修缺陷提交但含缺陷编号 | 3625 条 |

## A. 被判为「修缺陷提交」的抽样 —— 查**误判**

| # | commit | 提交时间 | 提交信息（截断） | 是修复吗？ | 备注 |
|---|---|---|---|---|---|
| 1 | `bd6059027325` | 2005-12-21 | added a test case and fixes for the pooled connection factory. AMQ-449  git-svn-id: https://svn.apache.org/rep… | 是 |  |
| 2 | `530884a2d991` | 2006-07-02 | Better protocol error handling. Fixed http://issues.apache.org/activemq/browse/AMQ-649    git-svn-id: https://… | 是 |  |
| 3 | `7dde85b82103` | 2006-11-20 | applied patch for http://issues.apache.org/activemq/browse/AMQ-959  git-svn-id: https://svn.apache.org/repos/a… | 是 |  |
| 4 | `955ceceea8e5` | 2007-06-22 | applied patch for AMQ-1270 from Dennis Byrne with thanks!  git-svn-id: https://svn.apache.org/repos/asf/active… | 是 |  |
| 5 | `3163d48eb16a` | 2008-01-09 | applied patch for https://issues.apache.org/activemq/browse/AMQ-1542  git-svn-id: https://svn.apache.org/repos… | 是 |  |
| 6 | `7a238556e389` | 2008-04-30 | Fix for https://issues.apache.org/activemq/browse/AMQ-1698  git-svn-id: https://svn.apache.org/repos/asf/activ… | 是 |  |
| 7 | `0cf384549ca8` | 2008-08-14 | Apply patch for https://issues.apache.org/activemq/browse/AMQ-1858  git-svn-id: https://svn.apache.org/repos/a… | 是 |  |
| 8 | `81f0cc0d0417` | 2008-10-23 | fix AMQ-1984 - hanging consumer receive after multiple consumer disconnect/reconnect  git-svn-id: https://svn.… | 是 |  |
| 9 | `c8e518b2dc3f` | 2009-03-30 | fix duplicate detection of messages recovered when space limit is reached and fix cursor cache reenablement wh… | 是 |  |
| 10 | `e7c9d2166005` | 2009-09-11 | Apply patch from https://issues.apache.org/activemq/browse/AMQ-2002  git-svn-id: https://svn.apache.org/repos/… | 是 |  |
| 11 | `3cbe3f1f921b` | 2010-03-09 | https://issues.apache.org/activemq/browse/AMQ-2440 - fixing bug on marking worker as non empty  git-svn-id: ht… | 是 |  |
| 12 | `8e70e010a030` | 2010-10-08 | resolve: https://issues.apache.org/activemq/browse/AMQ-2966 - related to fix for: https://issues.apache.org/ac… | 是 |  |
| 13 | `d5813be36088` | 2011-05-09 | https://issues.apache.org/jira/browse/AMQ-3305 - fix regression, only ask store for size while we are active, … | 是 |  |
| 14 | `ad76330eedd2` | 2011-09-29 | https://issues.apache.org/jira/browse/AMQ-3516  Add fix along with a unit test to ensure it stays fixed.  git-… | 是 |  |
| 15 | `5aa8b30c0fc2` | 2012-01-24 | fix and test for: https://issues.apache.org/jira/browse/AMQ-3675  git-svn-id: https://svn.apache.org/repos/asf… | 是 |  |
| 16 | `f77b2525a51e` | 2012-04-21 | Additional fix for: https://issues.apache.org/jira/browse/AMQ-3775  On remove of inner ListNode entries the It… | 是 |  |
| 17 | `b496c0a38c11` | 2012-08-28 | https://issues.apache.org/jira/browse/AMQ-3997 - Memory leak in activemq-pool. Apply patch from claus with tha… | 是 |  |
| 18 | `1942324dc3c5` | 2012-11-05 | Apply patch for: https://issues.apache.org/jira/browse/AMQ-4160  git-svn-id: https://svn.apache.org/repos/asf/… | 是 |  |
| 19 | `4d37271c5ae8` | 2013-01-14 | apply patch for: https://issues.apache.org/jira/browse/AMQ-4254  Add call to broker.waitUntilStopped() to try … | 是 |  |
| 20 | `6cdf756e9101` | 2013-03-19 | fix for: https://issues.apache.org/jira/browse/AMQ-4389  git-svn-id: https://svn.apache.org/repos/asf/activemq… | 是 |  |
| 21 | `539a5f162ebb` | 2013-06-06 | fix and test for: https://issues.apache.org/jira/browse/AMQ-4575  git-svn-id: https://svn.apache.org/repos/asf… | 是 |  |
| 22 | `9edc5d05115d` | 2013-09-28 | AMQ-4745: Upgrade to json-simple 1.1.1. Thanks to Jean Baptiste for the patch. | 否 | `AMQ-4745` 是依赖升级；`patch` 指「别人贡献的补丁」，不是修复动作 |
| 23 | `cce75e092665` | 2014-01-29 | https://issues.apache.org/jira/browse/AMQ-5001  Fix all failing tests. | 是（边界） | 修的是**测试代码**，非产品代码 —— 边界情形，未计入误判 |
| 24 | `bf1c57b33d2c` | 2014-07-09 | AMQ-5265 - fix race condition for task | 是 |  |
| 25 | `6df02555fde8` | 2015-04-01 | https://issues.apache.org/jira/browse/AMQ-5680  Fix typo in getTempQueues method. | 是 |  |
| 26 | `5b2aec54721f` | 2015-09-01 | AMQ-5935: fix earlier fluffed commit by removing old staging repo details | 否 | 修的是自己此前误入的 staging 仓库地址（元数据），非产品缺陷 |
| 27 | `28e7cb0b2182` | 2016-06-03 | https://issues.apache.org/jira/browse/AMQ-6309  Fix some minor issues shown by static code analysis | 是 |  |
| 28 | `e415d2921ec7` | 2017-02-01 | [AMQ-6587] ensure subs added to new destination before destination is exposed in the destination map. sort gc … | 是 |  |
| 29 | `83514ef799cb` | 2018-07-03 | AMQ-7001 - ensure cursor pending cached id list is pruned of futures that end in an exception, fix and test | 是 |  |
| 30 | `62cfe83e9d16` | 2020-05-21 | [AMQ-7291] rework fix to initializeWriting but just with the read only properties check | 是 |  |

## B. 未被判为「修缺陷提交」但含缺陷编号的抽样 —— 查**漏判**

| # | commit | 提交时间 | 提交信息（截断） | 其实是修复吗？ | 备注 |
|---|---|---|---|---|---|
| 1 | `27f7cab3e8be` | 2005-12-29 | added test case to show AMQ-458 working  git-svn-id: https://svn.apache.org/repos/asf/incubator/activemq/trunk… | 否 |  |
| 2 | `e8bae06604e3` | 2006-09-30 | Added unit test for consuming expired topic and queue. - AMQ-936  git-svn-id: https://svn.apache.org/repos/asf… | 否 |  |
| 3 | `1590da28a5b9` | 2008-09-16 | AMQ-1938: The pooled connection factory FactoryBean does not implement DisposableBean, thus leaking connection… | 是（边界） | 纯描述缺陷现象（leaking connections），未用修复动词 —— 未计入漏判 |
| 4 | `fbc5eb5eb051` | 2009-07-31 | Implemented:  https://issues.apache.org/activemq/browse/AMQ-2338  https://issues.apache.org/activemq/browse/AM… | 否 |  |
| 5 | `3a1bdc624957` | 2009-12-17 | https://issues.apache.org/activemq/browse/AMQ-2539 - adding temp destinations and security  git-svn-id: https:… | 否 |  |
| 6 | `093c90132947` | 2010-04-23 | https://issues.apache.org/activemq/browse/AMQ-2705 - broker version in jmx and web console  git-svn-id: https:… | 否 |  |
| 7 | `cf3db575a53a` | 2010-08-19 | resolve https://issues.apache.org/activemq/browse/AMQ-2840 - Eugene's carefull reading of the sepc results in … | 是 | 用的是 **`resolve`** —— JIRA 标准修复语，不在 D4 词表内 |
| 8 | `054fc6aca52f` | 2010-12-10 | https://issues.apache.org/jira/browse/AMQ-3081 - Durable subscriptions are not removed from mbean  git-svn-id:… | 是（边界） | 纯描述（are not removed from mbean）—— 未计入 |
| 9 | `24ed4fe5ae91` | 2011-04-07 | https://issues.apache.org/jira/browse/AMQ-3275 - make udp protocol work  git-svn-id: https://svn.apache.org/re… | 是（边界） | 「make udp protocol work」修坏掉的功能 —— 未计入 |
| 10 | `713dcaae564a` | 2011-08-26 | https://issues.apache.org/jira/browse/AMQ-3401 - pluggable unresolved destination trnasformer  git-svn-id: htt… | 否 |  |
| 11 | `5cd9ebaeb7f8` | 2012-03-21 | fis for: https://issues.apache.org/jira/browse/AMQ-3718  git-svn-id: https://svn.apache.org/repos/asf/activemq… | 是 | 写成 **`fis for:`**（`fix` 拼错），词首边界匹配不上 |
| 12 | `640424727d0d` | 2012-09-04 | https://issues.apache.org/jira/browse/AMQ-3998 https://issues.apache.org/jira/browse/AMQ-3999 - retroactive du… | 无法判定 | 提交信息在抽样表中被截断，信息不足 |
| 13 | `881c1b700517` | 2013-01-09 | https://issues.apache.org/jira/browse/AMQ-4237 - new jmx and list and purge commands  git-svn-id: https://svn.… | 否 |  |
| 14 | `edd8166cb1a4` | 2013-06-18 | https://issues.apache.org/jira/browse/AMQ-4574 - better initialization of destination source for camel endpoin… | 是（边界） | 描述式（better initialization）—— 未计入 |
| 15 | `3ed52ef8a247` | 2013-10-30 | Working on a test case for https://issues.apache.org/jira/browse/AMQ-4837 : LevelDB corrupted in AMQ cluster. | 否 |  |
| 16 | `c3d8ca716019` | 2014-02-27 | https://issues.apache.org/jira/browse/AMQ-5078 | 无法判定 | 提交信息只有 `AMQ-5078`，无任何动作描述 |
| 17 | `999385ea539c` | 2014-08-08 | https://issues.apache.org/jira/browse/AMQ-5316  remove unused configuration entry to reduce confusion, can be … | 否 |  |
| 18 | `05c31124021d` | 2015-02-18 | https://issues.apache.org/jira/browse/AMQ-5594 - virtual topics and wildcards | 否 |  |
| 19 | `551f4fc4e097` | 2015-05-19 | https://issues.apache.org/jira/browse/AMQ-5621  The tests no longer need to worry about configuring the schedu… | 否 |  |
| 20 | `4cddd2c01543` | 2015-09-15 | https://issues.apache.org/jira/browse/AMQ-5963  Disk limits can now be specified as a percentage of the partit… | 否 |  |
| 21 | `186b5d0f305e` | 2016-01-29 | https://issues.apache.org/jira/browse/AMQ-6113  Properly set the X-FRAME-OPTIONS header on web responses. | 是（边界） | 补缺失的安全头 —— 未计入 |
| 22 | `604f707d4d69` | 2016-05-10 | https://issues.apache.org/jira/browse/AMQ-6286 - refactor insertAtHead from pendinglist to ordered variant | 否 |  |
| 23 | `e91f5c8062f8` | 2016-10-07 | AMQ-6454 - ensure message.acknowledge throws if consumer has closed and message has been released broker side | 是（边界） | 「ensure … throws」—— 未计入 |
| 24 | `d2c0eddaad7a` | 2017-05-31 | [AMQ-6691] allow dlq flag to be set via jmx to allow retry op after a restart - use destinations element for l… | 否 |  |
| 25 | `dd3cac8f6cba` | 2018-07-04 | AMQ-5976 - sanitise filter display | 是（边界） | 「sanitise filter display」—— 未计入 |
| 26 | `d525096cac44` | 2019-10-18 | AMQ-7130 Update AMQ doap | 否 |  |
| 27 | `8cc5386fbbe7` | 2020-06-15 | AMQ-7497 - further test to verify behaviour after ra.stop | 否 |  |
| 28 | `c1a2ff25c127` | 2021-09-03 | [AMQ-8033] Remove activemq-camel (#701)  * [AMQ-8033] Remove activemq-camel   - Prerequisite for JMS v2.0 su… | 否 |  |
| 29 | `cd0423248d7f` | 2022-08-16 | [AMQ-9033] Upgrade to maven-project-info-reports-plugin 3.4.0 | 否 |  |
| 30 | `f70b1096bf24` | 2023-10-21 | AMQ-9321: Upgrade to maven-shade-plugin 3.5.1  (cherry picked from commit f13b5471ab3b2ac0a410336e7a5220284f58… | 否 |  |

## 复核结论（由复核人填写）

| 项 | 值 |
|---|---|
| A 组抽样条数 | 30 |
| A 组误判条数（判为修复、实为非修复） | **2** |
| **误判率** | **6.7%**（2 / 30） |
| B 组抽样条数 | 30 |
| B 组漏判条数（未判、实为修复） | **2** |
| **漏判率** | **6.7%**（2 / 30） |
| 复核人 | 苏哲勋（infra 线，**非打标作者**） |
| 复核日期 | 2026-09-18 |
| 复核对象 | 本文件 main @ `31cd4b6` |

**口径说明**：上表只计**无争议**的条目。另有 A 组 1 条、B 组 7 条属边界情形，单列在下面，
不计入上表 —— 若按「宽口径」（把边界一律计入），误判率 10.0%（3/30）、漏判率 30.0%（9/30）。
B 组另有 2 条因抽样表里提交信息截断/过短而**无法判定**。

### A 组：明确误判 2 条

| # | commit | 实际是什么 | 为什么判据会误收 |
|---|---|---|---|
| 22 | `9edc5d05115d` | 依赖升级（AMQ-4745，json-simple 1.1.1） | 含 `AMQ-4745` + `patch`，但原文是「Thanks to Jean Baptiste **for the patch**」—— `patch` 指别人贡献的补丁，不是修复动作 |
| 26 | `5b2aec54721f` | 修自己之前的烂提交（AMQ-5935，清理误入的 staging 仓库地址） | 含 `AMQ-5935` + `fix`，但修的是仓库元数据、不是产品缺陷 |

边界 1 条（未计入）：`cce75e092665`「AMQ-5001 Fix all failing tests.」—— 修的是测试代码；
修测试通常意味着产品回归，但字面上修的确实是测试。

### B 组：明确漏判 2 条

| # | commit | 实际是什么 | 为什么被判据漏掉 |
|---|---|---|---|
| 7 | `cf3db575a53a` | 修复（AMQ-2840） | 用的是 **`resolve`**，不在 `fix`/`bug`/`patch` 词表内 |
| 11 | `5cd9ebaeb7f8` | 修复（AMQ-3718） | 写成了 **`fis for:`**（`fix` 拼写错误），词首边界自然匹配不上 |

> 第 11 条落在**词首边界的已知外沿**上，不是实现没跟上判据：`\b(fix|bug|patch)` 能收 `fixinng`
> —— 它的头三个字母仍是 `fix`；而 `fis` 连头三个字母都不是 `fix`，任何边界规则都够不着。
> `docs/data-pipeline.md` 第 7 节与 `design.md` D4 已登记「收窄成严格词表会漏掉拼错的真修复」
> 这一权衡；本条的数值正是该外沿被量化的结果。

### 两条结论

**1. 误判方向（A 组）由「JIRA 号 + fix/patch 字样」的自然语言歧义造成，量很小（2/30）。**
两条都是「带修复词汇、但动作不是修缺陷」。要压到 0 只能靠语义分类，不值得做 ——
6.7% 的误判率在 SZZ 类工作里属可接受。

**2. 漏判方向（B 组）的 2 条都是「词表覆盖」问题，不是抽样偶然。**
D4 的词表是 `fix|bug|patch` —— `resolve` 不是这三者的任何词形变化，词首边界再宽也收不到；
`fis for:` 则拼错到连词首 `fix` 都不成立。两条都只能靠**扩词表**解决，成本几乎为零。

**建议**（不阻断 3.7，留给下一轮口径迭代）：在 D4 词表补 `resolve`/`resolved`；
拼写错误一项目前的边界只能覆盖「词首仍是 fix」的一类（如 `fixinng`），
`fis` / `fiix` 这类需显式白名单。
若要更稳，可对「带 AMQ 编号但无修复动词」的提交**单独打一个 `candidate` 标记**而不直接判负，
留人工复核 —— B 组那 7 条边界就在这个池子里。

> 本次复核**未改动任何数据或脚本**，只填了上述两栏与结论表。
