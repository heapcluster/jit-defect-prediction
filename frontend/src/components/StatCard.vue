<template>
  <div class="ui-metric">
    <div class="ui-metric__label">
      {{ label }}
    </div>
    <div
      class="ui-metric__value"
      :style="valueColor ? { color: valueColor } : null"
    >
      {{ value }}
    </div>
    <div
      v-if="hint"
      class="ui-metric__hint"
    >
      {{ hint }}
    </div>
  </div>
</template>

<script setup>
// 概览指标卡：与 JobResultPanel 的 .stat 瓦片共用同一套圆角、间距与字体层级。
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  hint: { type: String, default: '' },
  valueColor: { type: String, default: '' }
})
</script>

<style scoped>
.ui-metric {
  display: flex;
  flex: 1 1 0;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  background: linear-gradient(180deg, var(--ui-surface) 0%, var(--ui-surface-subtle) 100%);
  box-shadow: var(--ui-shadow-sm);
}
.ui-metric__label {
  color: var(--ui-text-muted);
  font-size: var(--ui-font-sm);
  font-weight: 550;
  white-space: nowrap;
}
.ui-metric__value {
  color: var(--ui-text);
  font-family: var(--ui-font-mono);
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.ui-metric__hint {
  overflow: hidden;
  color: var(--ui-text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
