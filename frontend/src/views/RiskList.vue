<template>
  <div>
    <h2>风险列表</h2>
    <el-empty description="待实现：按风险排序的提交列表 + 筛选 + 分页" />
  </div>
</template>

<script setup>
// 页面字段对照 docs/pages.md 第 2 节
// 接口：GET /api/commits（page/size/min_risk/model_name/start_time/end_time）
// 风险值：前端 ×100 转百分比；点击整行跳 /commit/:hash
</script>
