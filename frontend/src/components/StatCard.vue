<template>
  <div class="stat">
    <div class="k">
      {{ label }}
    </div>
    <div
      class="v"
      :style="valueColor ? { color: valueColor } : null"
    >
      {{ value }}
    </div>
    <div
      v-if="hint"
      class="h"
    >
      {{ hint }}
    </div>
  </div>
</template>

<script setup>
// 概览指标卡：一屏内先给数字，再给表格细节（页面引导性的主要载体之一）
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  hint: { type: String, default: '' },
  valueColor: { type: String, default: '' }
})
</script>

<style scoped>
.stat {
  flex: 1 1 0;
  min-width: 0;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff;
}
.k {
  font-size: 12px;
  color: #7c838c;
  white-space: nowrap;
}
.v {
  font-size: 24px;
  font-weight: 700;
  font-family: monospace;
  line-height: 1.25;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.h {
  font-size: 12px;
  color: #9aa1ab;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
