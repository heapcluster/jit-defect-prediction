<template>
  <div class="localization-inline">
    <div class="fields one">
      <label for="localization-inline-repo">
        仓库路径 / URL
        <input
          id="localization-inline-repo"
          v-model="repoSource"
          class="mono"
          placeholder="输入仓库路径或仓库地址"
          :disabled="running"
          @keyup.enter="run"
        >
      </label>
    </div>
    <div class="actions">
      <el-button
        type="primary"
        size="small"
        :loading="running"
        :disabled="!canRun"
        @click="run"
      >
        运行定位
      </el-button>
      <span
        v-if="running"
        class="ui-note"
      >正在定位…</span>
    </div>
    <p
      v-if="error"
      role="alert"
      class="validation"
    >
      {{ error }}
    </p>

    <template v-if="finished">
      <p class="ui-note">
        行级分档为服务端启发式优先程度，不是行级概率。
      </p>
      <p
        v-if="summaryText"
        class="ui-note"
      >
        {{ summaryText }}
      </p>
      <DataTable
        :columns="columns"
        :rows="previewRows"
        empty="暂无定位结果。"
        style="margin-top: 8px"
      >
        <template #[`cell.commit_hash`]="{ row }">
          <span
            class="mono"
            :title="row.commit_hash"
          >{{ shortHash(row.commit_hash) }}</span>
        </template>
        <template #[`cell.line_number`]="{ row }">
          {{ row.level === 'line' && row.line_number != null ? row.line_number : '—' }}
        </template>
        <template #[`cell.level`]="{ row }">
          {{ levelText(row.level) }}
        </template>
        <template #[`cell.suspicion`]="{ row }">
          {{ suspicionText(row.suspicion) }}
        </template>
        <template #[`cell.reason`]="{ row }">
          {{ reasonText(row) }}
        </template>
      </DataTable>
      <template v-if="suggestions">
        <p
          class="ui-note"
          style="margin-top: 12px"
        >
          <strong>修复建议（仅供参考）</strong>
        </p>
        <pre
          class="mono"
          style="margin: 8px 0 0; padding: 12px; border-radius: var(--ui-radius-md); background: var(--ui-surface-subtle); color: var(--ui-text); font-size: var(--ui-font-hint); line-height: 1.65; white-space: pre-wrap; overflow-wrap: anywhere;"
        >{{ suggestions }}</pre>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { fetchLocalizeOutput, runLocalize } from '../api'
import DataTable from './DataTable.vue'

const props = defineProps({
  commitHash: { type: String, required: true },
  modelName: { type: String, default: '' },
  prediction: { type: Object, default: null }
})

// 预测主表列顺序必须与后端 PREDICTIONS_COLUMNS 完全一致
const PREDICTION_COLUMNS = [
  'commit_hash',
  'model_name',
  'risk_score',
  'predicted_label',
  'decision_threshold',
  'model_version',
  'feature_version',
  'predicted_at',
  'is_bug_inducing'
]

const columns = [
  { key: 'commit_hash', label: '提交' },
  { key: 'file_path', label: '文件' },
  { key: 'line_number', label: '行号', align: 'right' },
  { key: 'level', label: '级别' },
  { key: 'suspicion', label: '可疑度', align: 'right' },
  { key: 'reason', label: '理由' }
]

const repoSource = ref('')
const running = ref(false)
const finished = ref(false)
const error = ref('')
const rows = ref([])
const summary = ref(null)
const suggestions = ref('')

const canRun = computed(() => Boolean(props.commitHash && repoSource.value.trim()))
const previewRows = computed(() => rows.value.slice(0, 50))
const summaryText = computed(() => {
  const value = summary.value
  if (!value) return ''
  const parts = []
  if (Number.isInteger(value.localized_rows)) parts.push(`${value.localized_rows} 条定位结果`)
  if (Number.isInteger(value.commits)) parts.push(`${value.commits} 个提交`)
  if (value.truncated) parts.push('结果已截断')
  return parts.length ? `本次共 ${parts.join('，')}。` : ''
})

function shortHash(hash) {
  return typeof hash === 'string' ? hash.slice(0, 8) : ''
}

function levelText(level) {
  if (level === 'line') return '行'
  if (level === 'commit') return '提交'
  return level || '—'
}

function suspicionText(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return '—'
  return `${(number * 100).toFixed(1)}%`
}

function reasonText(row) {
  if (typeof row.reason === 'string' && row.reason) return row.reason
  if (row.priority != null && row.priority !== '') return `优先程度 ${row.priority}`
  return '—'
}

function csvField(value) {
  const text = value == null ? '' : String(value)
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

// 用当前提交的预测构造单行预测表；predicted_at 缺失时补当前时间
function buildPredictionsFile() {
  const prediction = props.prediction || {}
  const values = {
    commit_hash: prediction.commit_hash ?? props.commitHash,
    model_name: prediction.model_name ?? props.modelName,
    risk_score: prediction.risk_score ?? '',
    predicted_label: prediction.predicted_label ?? '',
    decision_threshold: prediction.decision_threshold ?? '',
    model_version: prediction.model_version ?? '',
    feature_version: prediction.feature_version ?? '',
    predicted_at: prediction.predicted_at || new Date().toISOString(),
    is_bug_inducing: prediction.is_bug_inducing ?? ''
  }
  const csv = [
    PREDICTION_COLUMNS.join(','),
    PREDICTION_COLUMNS.map((key) => csvField(values[key])).join(',')
  ].join('\n')
  return new File([csv], 'predictions.csv', { type: 'text/csv' })
}

async function run() {
  if (!canRun.value || running.value) return
  running.value = true
  finished.value = false
  error.value = ''
  rows.value = []
  summary.value = null
  suggestions.value = ''
  try {
    const response = await runLocalize({
      repo_source: repoSource.value.trim(),
      commit_hash: props.commitHash,
      model_name: props.modelName || undefined,
      format: 'csv'
    }, [buildPredictionsFile()])

    const jobId = response?.job_id
    const evidenceName = `localization_evidence_${jobId}.json`
    const hasEvidence = Array.isArray(response?.outputs) &&
      response.outputs.some((item) => item?.name === evidenceName)
    if (!jobId || !hasEvidence) throw new Error('定位结果未生成完整证据文件')

    const parsed = JSON.parse(await (await fetchLocalizeOutput(jobId, evidenceName)).text())
    const document = parsed?.document && Array.isArray(parsed.document.rows) ? parsed.document : parsed
    rows.value = Array.isArray(document?.rows) ? document.rows : []
    summary.value = document?.summary || null
    suggestions.value = typeof response.suggestions === 'string' ? response.suggestions : ''
    finished.value = true
  } catch (caught) {
    error.value = caught?.detail || caught?.message || '定位失败，请稍后重试'
  } finally {
    running.value = false
  }
}
</script>
