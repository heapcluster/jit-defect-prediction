<template>
  <el-tag
    :type="type"
    :effect="effect"
    size="small"
  >
    {{ text }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

// 风险等级标签：优先用后端给的 level（读运行时阈值），没有才按分数兜底。
// 阈值与 utils/risk.js、后端 config 保持同一口径（0.5 / 0.2 为默认值）。
const HIGH = 0.5
const MID = 0.2

const props = defineProps({
  level: { type: String, default: '' },
  score: { type: Number, default: null },
  effect: { type: String, default: 'light' }
})

const text = computed(() => {
  if (props.level) return `${props.level}风险`
  if (props.score == null) return '未预测'
  if (props.score >= HIGH) return '高风险'
  if (props.score >= MID) return '中风险'
  return '低风险'
})

const type = computed(() => {
  if (props.level) {
    return { 高: 'danger', 中: 'warning', 低: 'success' }[props.level] || 'info'
  }
  if (props.score == null) return 'info'
  if (props.score >= HIGH) return 'danger'
  if (props.score >= MID) return 'warning'
  return 'success'
})
</script>
