# 契约三：接口格式

> 状态：**草案，未冻结** ｜ 版本 0.9 ｜ 定稿人 吕建江 ｜ 冻结时间 第 3 周中（9/23）

## 管什么

后端线要按这个格式返回，前端线要按这个格式渲染。**这是本项目改动最频繁的一条契约** —— 前端一抱怨「数据不够画图」，就容易临时改接口，改一次前端要跟着改一次。

## 一、通用约定

| 项 | 约定 | 理由 |
|---|---|---|
| 前缀 | 一律 `/api` | 便于将来与静态资源分开代理 |
| 响应包络 | `{ "code": 0, "message": "ok", "data": {...} }` | 成功失败结构一致，前端一套逻辑处理完 |
| 时间格式 | ISO 8601 带时区，例 `2026-09-16T08:30:00Z` | 前端 `new Date()` 可直接解析 |
| 概率字段 | 取值 `0.0` ~ `1.0` 的小数 | **前端自己转百分比**，后端不返回 `"85%"` 这种字符串 |
| 分页参数 | `page`（从 1 开始）、`size`（默认 20，上限 100） | 上限 100 是防止前端一次拉全表把接口拖慢 |
| 鉴权 | 请求头带令牌；未通过返回 401 | 对应课程「接口鉴权」要求 |

## 二、错误码表

| code | HTTP | 含义 | message 示例 |
|---|---|---|---|
| 0 | 200 | 成功 | `ok` |
| 40001 | 400 | 参数非法（类型错、越界、枚举值不存在） | `size 超过上限 100` |
| 40100 | 401 | 未通过鉴权 | `missing or invalid token` |
| 40400 | 404 | 目标不存在 | `commit not found` |
| 50000 | 500 | 服务内部错误 | `internal error` |

> **安全要求**：`50000` 的 message **不得回显异常堆栈、SQL 语句、文件路径**。课程明确要求「非法输入不泄露内部信息」。内部细节写进服务端日志，不返回给调用方。

## 三、接口清单

### 1. `GET /api/commits` —— 风险列表

按风险概率从高到低返回提交列表。对应前端「风险列表」页面。

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认 1 |
| `size` | int | 否 | 默认 20，上限 100 |
| `min_risk` | float | 否 | 只看风险概率不低于此值的提交，如 `0.5` |
| `model_name` | string | 否 | 指定模型版本，默认用最新 |
| `start_time` / `end_time` | string | 否 | ISO 8601 时间范围 |

**响应 `data`**

```json
{
  "total": 1284,
  "page": 1,
  "size": 20,
  "items": [
    {
      "commit_hash": "a1b2c3d4e5f6...",
      "author_name": "jdoe",
      "committed_at": "2026-08-14T09:12:33Z",
      "message": "AMQ-8123 fix NPE in broker shutdown",
      "risk_score": 0.8732,
      "model_name": "xgb_v1"
    }
  ]
}
```

### 2. `GET /api/commits/{commit_hash}` —— 提交详情

对应前端「提交详情」页面。回答「这一次提交为什么被判为高风险」。

**响应 `data`**

```json
{
  "commit_hash": "a1b2c3d4e5f6...",
  "author_name": "jdoe",
  "committed_at": "2026-08-14T09:12:33Z",
  "message": "AMQ-8123 fix NPE in broker shutdown",
  "risk_score": 0.8732,
  "model_name": "xgb_v1",
  "features": {
    "ns": 3, "nd": 5, "nf": 7, "entropy": 1.42,
    "la": 120, "ld": 44, "lt": 8600,
    "fix": 1,
    "ndev": 4, "age": 12.5, "nuc": 9,
    "exp": 320, "rexp": 45.2, "sexp": 18
  },
  "explanation": [
    { "feature": "entropy", "contribution": 0.21, "direction": "increase" },
    { "feature": "nuc",     "contribution": 0.14, "direction": "increase" },
    { "feature": "exp",     "contribution": 0.09, "direction": "decrease" }
  ]
}
```

**字段说明**：`features` 的键名必须与 `feature-columns.md` 完全一致。`explanation` 是模型解释（哪几项特征把风险推高、哪几项压低），供页面画特征贡献图。

### 3. `GET /api/trends` —— 缺陷引入趋势

对应前端「趋势看板」页面。

**请求参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `granularity` | string | 否 | `week`（默认）/ `month` |
| `start_time` / `end_time` | string | 否 | 时间范围 |
| `model_name` | string | 否 | 指定模型版本 |

**响应 `data`**

```json
{
  "granularity": "week",
  "model_name": "xgb_v1",
  "series": [
    { "period": "2026-W30", "commit_count": 42, "avg_risk": 0.31, "high_risk_count": 7 },
    { "period": "2026-W31", "commit_count": 55, "avg_risk": 0.36, "high_risk_count": 11 }
  ]
}
```

**「高风险」的判定阈值由前端配置还是后端返回？** 建议后端返回 `high_risk_count`，阈值定为参数（默认 `risk_score >= 0.5`），这样「高风险」的口径只有一处定义。

## 四、非功能要求与验证方式

| 要求 | 指标 | 怎么验证 | 证据形式 |
|---|---|---|---|
| 性能 | 预测接口 95% 的请求在 500ms 内返回 | 用脚本循环发 100 次请求，统计响应时间分位数 | 脚本 + 输出结果截图，放 `backend/` 或 `docs/` |
| 安全 | 接口需鉴权；非法输入不泄露内部信息 | ① 不带令牌请求，应返回 401；② 发送畸形参数，返回信息中不得含堆栈、SQL、路径 | 两组请求的返回结果截图 |

**这两条是课程明确的非功能要求，必须有可出示的证据。** 只写「已实现」不算。

## 五、不写进契约的

- 后端用什么 Web 框架、怎么组织路由
- 前端用什么请求库、怎么做状态管理
- 接口的部署地址与端口（属于运行配置）
- 内部模块之间怎么调用

## 待确认

- [ ] 三个接口是否够画三个页面 —— 待刘帅华确认（尤其趋势看板是否需要按作者/子系统分组）
- [ ] 鉴权方式：固定令牌 / JWT / 其他 —— 待吕建江定
- [ ] `explanation` 的具体算法（SHAP / 特征重要性）待模型线确定后回填

## 变更日志

| 日期 | 版本 | 变更人 | 主要变更 |
|---|---|---|---|
| 2026-09-16 | 0.9 | 蒋励 | 初版草案：通用约定、错误码表、三个接口、非功能要求验证方式 |
