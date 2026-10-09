<template>
  <div>
    <h2>缺陷引入趋势看板</h2>
    <el-empty description="待实现：按周/月聚合的风险趋势图 + 汇总 + 明细" />
  </div>
</template>

<script setup>
// 页面字段对照 docs/pages.md 第 4 节
// 接口：GET /api/trends（granularity/model_name/start_time/end_time）
// 图表统一用 ECharts；平均风险直接按 0~1 画轴，不必转百分比
</script>
