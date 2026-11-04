<template>
  <span class="cascade">
    <el-select
      :model-value="line"
      placeholder="全部架构"
      clearable
      style="width: 130px"
      @update:model-value="onLineChange"
    >
      <el-option
        v-for="l in lines"
        :key="l.line"
        :label="l.label"
        :value="l.line"
        :disabled="!l.models.length"
      />
    </el-select>
    <el-select
      :model-value="model"
      :placeholder="modelPlaceholder"
      clearable
      style="width: 180px"
      :disabled="!line"
      @update:model-value="onModelChange"
    >
      <el-option
        v-for="m in currentModels"
        :key="m"
        :label="m"
        :value="m"
      />
    </el-select>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  lines: { type: Array, default: () => [] },
  line: { type: String, default: '' },
  model: { type: String, default: '' },
  // 模型下拉的占位文案：查询/趋势/模型性能用「全部模型」，详情重预测用「默认模型」
  modelPlaceholder: { type: String, default: '全部模型' }
})

const emit = defineEmits(['update:line', 'update:model'])

const currentModels = computed(() => {
  const picked = props.lines.find((l) => l.line === props.line)
  return picked ? picked.models : []
})

function onLineChange(value) {
  emit('update:line', value || '')
  // 切换架构清空已选模型（docs/web_page：两级联动，切换架构清空模型）
  if (props.model) emit('update:model', '')
}

function onModelChange(value) {
  emit('update:model', value || '')
}
</script>

<style scoped>
.cascade {
  display: inline-flex;
  gap: 8px;
}
</style>
