<template>
  <div
    v-if="rows.length"
    class="info-card"
  >
    <div class="info-grid">
      <div
        v-for="row in rows"
        :key="row.label"
        class="info-row"
        :class="{ 'span-two': row.span }"
      >
        <span class="info-label">{{ row.label }}</span>
        <span
          class="info-value"
          :class="{ mono: row.mono }"
        >{{ row.value ?? '—' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
// 预测 / 评估结果区的本次运行摘要结构完全一致，统一由这里渲染。
defineOptions({ name: 'JobSummaryCard' })
defineProps({ rows: { type: Array, default: () => [] } })
</script>
