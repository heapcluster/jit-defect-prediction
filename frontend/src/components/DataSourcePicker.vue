<template>
  <div class="picker">
    <div class="seg" role="tablist">
      <button
        class="seg-item"
        :class="{ active: kind === 'dataset' }"
        :disabled="disabled"
        role="tab"
        :aria-selected="kind === 'dataset'"
        @click="setKind('dataset')"
      >
        已保存数据集
      </button>
      <button
        class="seg-item"
        :class="{ active: kind === 'file' }"
        :disabled="disabled"
        role="tab"
        :aria-selected="kind === 'file'"
        @click="setKind('file')"
      >
        上传文件
      </button>
    </div>

    <div v-if="kind === 'dataset'" class="control">
      <el-select
        v-model="selectedId"
        filterable
        clearable
        placeholder="请选择数据集"
        :disabled="disabled"
        style="width: 100%"
        @change="onDataset"
      >
        <el-option v-for="item in datasets" :key="item.dataset_id" :value="item.dataset_id" :label="item.name">
          <div class="option">
            <span>{{ item.name }}</span>
            <span class="soft mono">{{ lineLabel(item.line) }} · {{ item.sample_count }} 行</span>
          </div>
        </el-option>
      </el-select>
      <div v-if="!datasets.length" class="hint">暂无可选数据集，可先到数据收集或数据清洗页保存。</div>
    </div>

    <div v-else class="control">
      <input ref="inputRef" type="file" accept=".csv,.xlsx" hidden @change="onFile" />
      <el-button :disabled="disabled" @click="inputRef?.click()">选择文件</el-button>
      <span class="file-name" :class="{ soft: !fileName }">{{ fileName || '支持 CSV / Excel，Excel 只读取第一个工作表' }}</span>
    </div>

    <div v-if="loading" class="loading">
      <span class="spinner" /> 正在校验字段契约…
    </div>

    <div v-if="error" class="result error">
      <strong>校验未通过</strong>
      <span>{{ error }}</span>
    </div>

    <div v-else-if="info" class="result">
      <span class="pill primary">{{ lineLabel(info.line) }}</span>
      <span class="pill">{{ info.sample_count }} 行</span>
      <template v-if="info.has_label">
        <span class="pill success">正 {{ info.pos ?? 0 }}</span>
        <span class="pill">负 {{ info.neg ?? 0 }}</span>
      </template>
      <span v-else class="pill warning">无真实标签</span>
      <span v-if="info.kind === 'file'" class="code-chip">{{ info.label }}</span>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { humanError, LINE } from '../utils/format'

const props = defineProps({
  datasets: { type: Array, default: () => [] },
  importApi: { type: Function, required: true },
  precheckApi: { type: Function, required: true },
  mode: { type: String, default: 'clean' },
  disabled: { type: Boolean, default: false },
  initialSource: { type: Object, default: null },
  initialInfo: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'validated'])

const kind = ref('dataset')
const selectedId = ref('')
const fileName = ref('')
const loading = ref(false)
const error = ref('')
const info = ref(null)
const inputRef = ref(null)

function lineLabel(line) {
  return LINE[line] || line || '—'
}

function clearSelection() {
  selectedId.value = ''
  fileName.value = ''
  info.value = null
  error.value = ''
  emit('update:modelValue', null)
  emit('validated', null)
}

function reset() {
  kind.value = 'dataset'
  clearSelection()
}

function setKind(value) {
  if (kind.value === value) return
  kind.value = value
  clearSelection()
}

function normalizeDataset(data, id) {
  const pos = data.pos ?? data.pos_count ?? null
  const neg = data.neg ?? data.neg_count ?? null
  const item = props.datasets.find((entry) => entry.dataset_id === id)
  return {
    kind: 'dataset',
    id,
    label: item?.name || data.name || id,
    line: data.line || item?.line || 'expert',
    sample_count: data.sample_count ?? item?.sample_count ?? 0,
    pos,
    neg,
    has_label: data.has_label ?? (props.mode !== 'predict' || pos !== null),
    repo_available: data.repo_available ?? false,
    columns: data.columns || []
  }
}

function normalizeFile(data, file) {
  const pos = data.pos ?? null
  const neg = data.neg ?? null
  return {
    kind: 'file',
    id: data.file_id,
    label: file.name,
    line: data.line || 'expert',
    sample_count: data.sample_count ?? data.row_count ?? 0,
    pos,
    neg,
    has_label: data.has_label ?? (Array.isArray(data.columns) ? data.columns.includes('bug') : props.mode !== 'predict'),
    columns: data.columns || [],
    repo_available: false
  }
}

async function onDataset(id) {
  info.value = null
  error.value = ''
  emit('update:modelValue', null)
  emit('validated', null)
  if (!id) return
  loading.value = true
  try {
    const data = await props.precheckApi(id)
    info.value = normalizeDataset(data, id)
    emit('update:modelValue', { kind: 'dataset', id, label: info.value.label })
    emit('validated', info.value)
  } catch (requestError) {
    error.value = humanError(requestError)
  } finally {
    loading.value = false
  }
}

async function onFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  info.value = null
  error.value = ''
  emit('update:modelValue', null)
  emit('validated', null)
  loading.value = true
  fileName.value = file.name
  try {
    const data = await props.importApi(file)
    info.value = normalizeFile(data, file)
    emit('update:modelValue', { kind: 'file', id: info.value.id, label: file.name })
    emit('validated', info.value)
  } catch (requestError) {
    error.value = humanError(requestError)
  } finally {
    loading.value = false
  }
}

function applyInitial(source, detail) {
  if (!source) return
  kind.value = source.kind === 'file' ? 'file' : 'dataset'
  selectedId.value = source.kind === 'dataset' ? source.id : ''
  fileName.value = source.kind === 'file' ? source.label || '' : ''
  info.value = detail || null
}

defineExpose({ reset })

onMounted(() => applyInitial(props.initialSource, props.initialInfo))

// 页面进度是异步恢复的：挂载时拿不到初值，这里在恢复写入后补齐展示。
watch(
  () => [props.initialSource, props.initialInfo],
  ([source, detail]) => {
    if (!source || info.value || loading.value) return
    applyInitial(source, detail)
  }
)
</script>

<style scoped>
.picker {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.seg {
  display: inline-flex;
  padding: 4px;
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 11px;
  width: fit-content;
}

.seg-item {
  border: 0;
  background: transparent;
  color: var(--text-muted);
  font-weight: 600;
  font-size: 12.5px;
  padding: 7px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.15s ease;
}

.seg-item.active {
  background: var(--surface);
  color: var(--primary-strong);
  box-shadow: var(--shadow-sm);
}

.seg-item:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.control {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.file-name {
  font-size: 12.5px;
  color: var(--text);
}

.hint {
  font-size: 12px;
  color: var(--text-soft);
}

.loading {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--text-muted);
}

.spinner {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--border-strong);
  border-top-color: var(--primary);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.result {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  border: 1px solid var(--border);
  font-size: 12.5px;
}

.result.error {
  background: var(--danger-soft);
  border-color: rgba(214, 69, 69, 0.2);
  color: #7f1d1d;
  display: block;
}

.result.error strong {
  display: block;
  margin-bottom: 3px;
}

.option {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
</style>
