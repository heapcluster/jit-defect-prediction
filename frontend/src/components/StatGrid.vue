<template>
  <div class="ui-stat-grid">
    <StatCard
      v-for="item in items"
      :key="item.key || item.label"
      :label="item.label"
      :value="item.value ?? '—'"
      :hint="item.hint"
      :value-color="item.valueColor || ''"
    />
  </div>
</template>

<script setup>
import StatCard from './StatCard.vue'

// 统计卡栅格：所有页面的指标组都走 StatCard，避免各自维护 .stat 样式。
defineOptions({ name: 'StatGrid' })
defineProps({
  // item: { key?, label, value?, hint?, valueColor? }
  items: { type: Array, default: () => [] }
})
</script>
