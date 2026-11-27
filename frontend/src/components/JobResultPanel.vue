<template>
  <section
    v-if="show"
    class="panel"
    data-pane="wide"
    :aria-label="title"
    :data-testid="testId"
  >
    <div class="section-heading">
      <h2>{{ title }}</h2>
    </div>
    <StatGrid :items="stats" />
    <!-- 插槽顺序与数据清洗页一致：统计 → 附加提示 → 错误 → 摘要 → 折叠区 -->
    <slot name="notices" />
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
    />
    <JobSummaryCard
      v-if="summaryRows.length"
      :rows="summaryRows"
    />
    <slot />
  </section>
</template>

<script setup>
import JobSummaryCard from './JobSummaryCard.vue'
import StatGrid from './StatGrid.vue'

// 预测 / 评估 / 清洗的结果区共用同一结构：标题、统计、错误提示、摘要卡与页面专属折叠区。
defineOptions({ name: 'JobResultPanel' })
defineProps({
  title: { type: String, required: true },
  testId: { type: String, required: true },
  stats: { type: Array, default: () => [] },
  error: { type: String, default: '' },
  summaryRows: { type: Array, default: () => [] },
  show: { type: Boolean, default: true }
})
</script>
