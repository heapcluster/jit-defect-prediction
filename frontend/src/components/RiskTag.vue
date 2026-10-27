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
import { riskLevel, riskTag } from '../utils/risk'

// 风险等级标签：优先用后端给的 level（读运行时阈值），没有才按当前阈值兜底。
// 两条路径共用 utils/risk.js，阈值只存在一处（/api/config）。
const props = defineProps({
  level: { type: String, default: '' },
  score: { type: Number, default: null },
  effect: { type: String, default: 'light' }
})

const text = computed(() => `${props.level || riskLevel(props.score) || '?'}风险`)

const type = computed(() => {
  if (props.level) return { 高: 'danger', 中: 'warning', 低: 'success' }[props.level] || 'info'
  return riskTag(props.score)
})
</script>
