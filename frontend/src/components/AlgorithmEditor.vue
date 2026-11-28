<template>
  <div class="algo-editor">
    <div class="row-between toolbar">
      <span class="muted">已选 <strong>{{ selected.length }}</strong> / {{ algorithms.length }}</span>
      <div class="row">
        <el-button size="small" :disabled="disabled" @click="selectAll">全选</el-button>
        <el-button size="small" :disabled="disabled" @click="clearAll">清空</el-button>
      </div>
    </div>

    <div class="algo-grid">
      <div
        v-for="item in algorithms"
        :key="item.algo"
        class="algo-card"
        :class="{ on: isSelected(item.algo), disabled }"
      >
        <div class="algo-head">
          <el-checkbox
            :model-value="isSelected(item.algo)"
            :disabled="disabled"
            @change="(value) => toggle(item, value)"
          >
            <span class="algo-name">{{ item.algo }}</span>
          </el-checkbox>
          <span class="pill">{{ familyLabel(item.family) }}</span>
        </div>
        <div v-if="isSelected(item.algo)" class="params">
          <label v-for="(value, key) in paramsOf(item.algo)" :key="key" class="param">
            <span>{{ paramLabel(key) }}</span>
            <el-input-number
              v-if="typeof defaultsOf(item.algo)[key] === 'number'"
              :model-value="Number(value)"
              :disabled="disabled"
              :controls="false"
              size="small"
              @update:model-value="(next) => setParam(item.algo, key, next)"
            />
            <el-input
              v-else
              :model-value="displayValue(value)"
              :disabled="disabled"
              size="small"
              @update:model-value="(next) => setParam(item.algo, key, parseValue(defaultsOf(item.algo)[key], next))"
            />
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  algorithms: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue'])
const selected = ref([])

const FAMILY = {
  linear: '线性',
  tree: '树模型',
  ensemble: '集成',
  boosting: '提升树',
  svm: '支持向量机',
  neighbor: '近邻',
  neural: '神经网络'
}

const PARAM_LABEL = {
  C: 'C',
  max_iter: '最大迭代',
  max_depth: '最大深度',
  min_samples_split: '最小分裂样本',
  n_estimators: '树数量',
  learning_rate: '学习率',
  num_leaves: '叶子数',
  kernel: '核函数',
  gamma: 'gamma',
  n_neighbors: '近邻数',
  weights: '权重',
  hidden_layers: '隐藏层',
  alpha: 'alpha',
  dropout: 'Dropout',
  epochs: '训练轮数',
  batch_size: '批大小',
  n_d: 'n_d',
  n_a: 'n_a'
}

function familyLabel(value) {
  return FAMILY[value] || value || '—'
}

function paramLabel(key) {
  return PARAM_LABEL[key] || key
}

function defaultsOf(algo) {
  return props.algorithms.find((item) => item.algo === algo)?.defaults || {}
}

function paramsOf(algo) {
  return selected.value.find((item) => item.algo === algo)?.params || {}
}

function isSelected(algo) {
  return selected.value.some((item) => item.algo === algo)
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function sync(value) {
  const normalized = (value || []).map((item) => ({
    algo: item.algo,
    params: { ...clone(defaultsOf(item.algo)), ...(item.params || {}) }
  }))
  if (JSON.stringify(normalized) !== JSON.stringify(selected.value)) {
    selected.value = normalized
  }
}

watch(() => props.modelValue, sync, { deep: true, immediate: true })

function emitSelected() {
  emit('update:modelValue', selected.value.map((item) => ({ algo: item.algo, params: { ...item.params } })))
}

function toggle(item, checked) {
  if (checked) {
    if (!isSelected(item.algo)) {
      selected.value.push({ algo: item.algo, params: clone(item.defaults || {}) })
    }
  } else {
    selected.value = selected.value.filter((entry) => entry.algo !== item.algo)
  }
  emitSelected()
}

function selectAll() {
  selected.value = props.algorithms.map((item) => ({ algo: item.algo, params: clone(item.defaults || {}) }))
  emitSelected()
}

function clearAll() {
  selected.value = []
  emitSelected()
}

function setParam(algo, key, value) {
  const entry = selected.value.find((item) => item.algo === algo)
  if (!entry) return
  entry.params[key] = value
  emitSelected()
}

function displayValue(value) {
  return Array.isArray(value) ? value.join(', ') : String(value ?? '')
}

function parseValue(original, text) {
  if (Array.isArray(original)) {
    return String(text)
      .split(',')
      .map((part) => Number(part.trim()))
      .filter((number) => Number.isFinite(number))
  }
  return text
}
</script>

<style scoped>
.algo-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar {
  padding-bottom: 2px;
}

.algo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 10px;
}

.algo-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-muted);
  padding: 12px;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.algo-card.on {
  background: #fbfefd;
  border-color: rgba(15, 118, 110, 0.36);
  box-shadow: 0 8px 22px rgba(15, 118, 110, 0.08);
}

.algo-card.disabled {
  opacity: 0.6;
}

.algo-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.algo-name {
  font-family: var(--mono);
  font-weight: 700;
  color: var(--text);
}

.params {
  margin-top: 10px;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
}

.param {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .algo-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
