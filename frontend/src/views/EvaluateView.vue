<template>
  <div class="stack">
    <PageHeader title="模型评估" subtitle="对带标签的预测结果计算指标、生成图表并留存历史" eyebrow="Pipeline 05">
      <template #actions>
        <div class="seg" role="tablist">
          <button class="seg-item" :class="{ active: state.mode === 'new' }" role="tab" :aria-selected="state.mode === 'new'" @click="setMode('new')">
            新建评估
          </button>
          <button class="seg-item" :class="{ active: state.mode === 'history' }" role="tab" :aria-selected="state.mode === 'history'" @click="setMode('history')">
            历史评估
          </button>
        </div>
        <el-button @click="confirmReset">重置</el-button>
      </template>
    </PageHeader>

    <div v-if="page.syncError" class="pill warning">进度未同步：{{ page.syncError }}</div>

    <template v-if="state.mode === 'new'">
      <SectionCard index="01" title="选择预测结果" description="仅接受带真实标签的预测结果数据集，或符合契约的预测结果文件">
        <div class="grid-2">
          <div class="field">
            <label class="field-label" for="eval-dataset">预测结果数据集</label>
            <el-select
              id="eval-dataset"
              v-model="selectedDatasetId"
              filterable
              clearable
              placeholder="请选择预测结果数据集"
              :disabled="running"
              style="width: 100%"
              @change="onDataset"
            >
              <el-option
                v-for="item in predictionDatasets"
                :key="item.dataset_id"
                :value="item.dataset_id"
                :label="item.name"
                :disabled="unusableIds.includes(item.dataset_id)"
              >
                <div class="option">
                  <span>{{ item.name }}</span>
                  <span class="soft">{{ item.sample_count }} 行</span>
                </div>
              </el-option>
            </el-select>
            <div v-if="!predictionDatasets.length" class="hint">还没有预测结果数据集，可先到模型预测页生成并保存。</div>
          </div>

          <div class="field">
            <label class="field-label">导入预测结果文件</label>
            <div class="row wrap">
              <input ref="fileInput" type="file" accept=".csv,.xlsx" hidden @change="onFile" />
              <el-button :loading="importing" :disabled="running" @click="fileInput?.click()">选择文件</el-button>
              <el-input v-model="state.importLabel" placeholder="显示名（默认外部预测结果）" style="max-width: 230px" :disabled="running" />
            </div>
            <div class="hint">文件表头为原始数据集列（含 `bug`）加 `risk_score`、`predicted_label`、`threshold`。</div>
            <div v-if="sourceError" class="form-error">{{ sourceError }}</div>
          </div>
        </div>

        <div v-if="state.sourceInfo" class="recognized">
          <span class="pill primary">{{ LINE[state.sourceInfo.line] || state.sourceInfo.line }}</span>
          <span class="pill">模型 {{ modelDisplay }}</span>
          <span class="pill">样本 {{ state.sourceInfo.sample_count }}</span>
          <span class="pill success">正 {{ state.sourceInfo.pos }}</span>
          <span class="pill">负 {{ state.sourceInfo.neg }}</span>
          <span class="pill">阈值 {{ thresholdText(state.sourceInfo.threshold) }}</span>
        </div>
      </SectionCard>

      <SectionCard index="02" title="指标与阈值" description="至少选择 1 项；单类别数据不能计算 AUC / AP">
        <div class="metric-grid">
          <label v-for="item in METRIC_OPTIONS" :key="item.value" class="metric-item" :class="{ off: singleClass && item.optional }">
            <el-checkbox
              :model-value="state.metrics.includes(item.value)"
              :disabled="running || (singleClass && item.optional)"
              @change="(checked) => toggleMetric(item.value, checked)"
            >
              {{ item.label }}
            </el-checkbox>
            <span v-if="singleClass && item.optional" class="soft">单类别不可用</span>
          </label>
        </div>
        <p v-if="!state.metrics.length" class="form-error">至少选择一个指标。</p>

        <div class="threshold-row">
          <span class="field-label">阈值</span>
          <el-slider v-model="state.threshold" :min="0" :max="1" :step="0.01" :disabled="running" />
          <el-input-number
            v-model="state.threshold"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="2"
            :controls="false"
            :disabled="running"
            style="width: 110px"
          />
          <span class="muted">概率 ≥ 阈值判为缺陷</span>
        </div>
        <p v-if="!thresholdValid" class="form-error">阈值必须位于 0–1。</p>
      </SectionCard>

      <SectionCard index="03" title="执行评估" description="图表按勾选条件生成；运行中锁定输入">
        <template v-if="job">
          <JobPanel
            :job="job"
            :elapsed="elapsed"
            :progress="progress"
            :is-running="isRunning"
            :is-success="isSuccess"
            :is-failed="isFailed"
            @cancel="cancelJob"
          />
          <div v-if="isCancelled" class="form-error">任务已取消，本轮结果已丢弃。</div>
        </template>
        <div v-else class="muted">开始评估后，这里显示图表生成进度与耗时。</div>
        <template #footer>
          <span class="muted">{{ plannedFigureText }}</span>
          <el-button type="primary" :disabled="!canRun" :loading="starting" @click="startEvaluate">开始评估</el-button>
        </template>
      </SectionCard>

      <SectionCard v-if="result" index="04" title="评估结果" description="指标只显示本次勾选项；图表可单独下载">
        <template #aside>
          <span class="pill">阈值 {{ Number(result.threshold).toFixed(2) }}</span>
          <span class="pill">样本 {{ result.sample_count }}</span>
        </template>

        <div class="result-grid">
          <el-table :data="metricRows" border size="small" class="metric-table">
            <el-table-column prop="name" label="指标" width="140" />
            <el-table-column label="值" align="right">
              <template #default="{ row }">{{ formatPercent(row.value) }}</template>
            </el-table-column>
          </el-table>

          <div class="figure-grid">
            <figure v-for="fig in result.figures" :key="fig.type" class="figure-card">
              <figcaption>
                <strong>{{ FIGURE_LABEL[fig.type] || fig.type }}</strong>
                <div class="row">
                  <el-button link type="primary" :loading="downloadingFigure === fig.type" @click="downloadFigure(fig.type)">下载 PNG</el-button>
                </div>
              </figcaption>
              <div v-if="figureFailed[`r-${fig.type}`]" class="figure-failed">
                <span>生成失败</span>
                <el-button size="small" @click="retryFigure(`r-${fig.type}`)">重试</el-button>
              </div>
              <img
                v-else
                :src="`${fig.url}?v=${figureVersion}`"
                :alt="FIGURE_LABEL[fig.type] || fig.type"
                @error="figureFailed[`r-${fig.type}`] = true"
              />
            </figure>
          </div>
        </div>

        <div class="export-row">
          <el-input v-model="state.exportName" placeholder="导出文件名（不含扩展名）" style="max-width: 280px" />
          <el-button :loading="exporting" @click="exportAs('csv')">导出 CSV</el-button>
          <el-button :loading="exporting" @click="exportAs('excel')">导出 Excel</el-button>
        </div>

        <template #footer>
          <div class="row wrap grow">
            <span class="muted">保存后可在「历史评估」中查看；名称在同一用户内不可重复。</span>
            <el-input v-model="state.saveName" placeholder="评估名称" style="max-width: 260px" />
          </div>
          <div class="row">
            <span v-if="state.savedEvaluationId" class="pill success">已保存 {{ state.savedEvaluationId }}</span>
            <el-button type="primary" :loading="saving" :disabled="!canSave" @click="saveEvaluation">
              保存到评估历史
            </el-button>
          </div>
        </template>
      </SectionCard>
    </template>

    <template v-else>
      <SectionCard title="历史评估" description="按生成时间倒序；删除历史不影响预测结果数据集与模型">
        <template #aside>
          <el-input v-model="historyQuery" clearable placeholder="搜索名称" style="width: 190px" @keyup.enter="resetHistoryPage" @clear="resetHistoryPage" />
          <el-button size="small" :loading="history.loading" @click="resetHistoryPage">刷新</el-button>
        </template>

        <div v-if="history.error">
          <ErrorState :message="history.error" @retry="loadHistory" />
        </div>
        <EmptyState
          v-else-if="!history.loading && !history.items.length"
          title="还没有保存的评估"
          description="保存的评估会出现在这里，可重新查看指标与图表。"
        >
          <template #action>
            <el-button type="primary" @click="setMode('new')">新建评估</el-button>
          </template>
        </EmptyState>
        <template v-else>
          <el-table v-loading="history.loading" :data="history.items" border>
            <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
            <el-table-column label="来源" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">{{ row.source_label || (row.source_kind === 'dataset' ? '数据集' : '外部文件') }}</template>
            </el-table-column>
            <el-table-column label="模型" min-width="170" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="mono">{{ row.model_label || (row.source_kind === 'file' ? '外部预测结果' : '—') }}</span>
              </template>
            </el-table-column>
            <el-table-column label="阈值" width="90" align="right">
              <template #default="{ row }">{{ Number(row.threshold).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="指标摘要" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">{{ summaryOf(row.metrics) }}</template>
            </el-table-column>
            <el-table-column label="生成时间" width="176">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openHistory(row)">查看</el-button>
                <el-button link type="danger" @click="removeHistory(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager">
            <el-pagination
              v-model:current-page="history.page"
              :page-size="history.page_size"
              :total="history.total"
              layout="total, prev, pager, next"
              :hide-on-single-page="true"
              @current-change="loadHistory"
            />
          </div>
        </template>
      </SectionCard>
    </template>

    <el-drawer v-model="historyOpen" :title="historyDetail?.name || '评估详情'" size="660px" destroy-on-close>
      <div v-if="historyLoading" class="stack">
        <el-skeleton :rows="4" animated />
      </div>
      <ErrorState v-else-if="historyDetailError" :message="historyDetailError" @retry="loadHistoryDetail" />
      <div v-else-if="historyDetail" class="drawer stack">
        <div class="row wrap">
          <span class="pill primary">{{ historyDetail.source_kind === 'dataset' ? '预测结果数据集' : '外部文件' }}</span>
          <span class="pill">模型 {{ historyDetail.model_label || (historyDetail.source_kind === 'file' ? '外部预测结果' : '—') }}</span>
          <span class="pill">阈值 {{ Number(historyDetail.threshold).toFixed(2) }}</span>
          <span class="pill">样本 {{ historyDetail.sample_count }}</span>
          <span class="pill">{{ formatTime(historyDetail.created_at) }}</span>
        </div>

        <el-table :data="historyMetricRows" border size="small">
          <el-table-column prop="name" label="指标" width="140" />
          <el-table-column label="值" align="right">
            <template #default="{ row }">{{ formatPercent(row.value) }}</template>
          </el-table-column>
        </el-table>

        <div class="figure-grid">
          <figure v-for="fig in historyDetail.figures" :key="fig.type" class="figure-card">
            <figcaption>
              <strong>{{ FIGURE_LABEL[fig.type] || fig.type }}</strong>
              <el-button link type="primary" :loading="downloadingFigure === `h-${fig.type}`" @click="downloadHistoryFigure(fig.type)">下载 PNG</el-button>
            </figcaption>
            <div v-if="figureFailed[`h-${fig.type}`]" class="figure-failed">
              <span>生成失败</span>
              <el-button size="small" @click="retryFigure(`h-${fig.type}`)">重试</el-button>
            </div>
            <img
              v-else
              :src="`${historyFigureSrc(fig.type)}?v=${figureVersion}`"
              :alt="FIGURE_LABEL[fig.type] || fig.type"
              @error="figureFailed[`h-${fig.type}`] = true"
            />
          </figure>
        </div>

        <div class="export-row">
          <span class="muted">只读详情，可重新导出，不可重新计算。</span>
          <el-button :loading="exporting" @click="exportHistoryAs('csv')">导出 CSV</el-button>
          <el-button :loading="exporting" @click="exportHistoryAs('excel')">导出 Excel</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import SectionCard from '../components/SectionCard.vue'
import JobPanel from '../components/JobPanel.vue'
import EmptyState from '../components/EmptyState.vue'
import ErrorState from '../components/ErrorState.vue'
import { listDatasets } from '../api/datasets'
import { getJob } from '../api/jobs'
import * as evaluateApi from '../api/evaluate'
import { humanError, formatTime, formatPercent, shortId, LINE, METRIC_LABEL, FIGURE_LABEL } from '../utils/format'
import { saveBlob } from '../utils/download'
import { useJob } from '../composables/useJob'
import { usePageState } from '../composables/usePageState'

const METRIC_OPTIONS = [
  { value: 'accuracy', label: '准确率' },
  { value: 'precision', label: '精确率' },
  { value: 'recall', label: '召回率' },
  { value: 'f1', label: 'F1' },
  { value: 'auc', label: 'AUC', optional: true },
  { value: 'ap', label: 'AP', optional: true },
  { value: 'mcc', label: 'MCC' }
]

function defaults() {
  return {
    mode: 'new',
    step: 1,
    source: null,
    sourceInfo: null,
    importLabel: '',
    metrics: ['accuracy', 'precision', 'recall', 'f1', 'auc', 'ap'],
    threshold: 0.5,
    job_id: null,
    result_ref: null,
    exportName: '',
    saveName: '',
    savedName: '',
    savedEvaluationId: null
  }
}

const page = usePageState('evaluate', defaults)
const state = page.state
const predictionDatasets = ref([])
const selectedDatasetId = ref('')
const unusableIds = ref([])
const fileInput = ref(null)
const importing = ref(false)
const sourceError = ref('')
const starting = ref(false)
const exporting = ref(false)
const saving = ref(false)
const result = ref(null)
const figureVersion = ref(0)
const figureFailed = reactive({})
const downloadingFigure = ref('')

const history = reactive({ items: [], total: 0, page: 1, page_size: 20, loading: false, error: '' })
const historyQuery = ref('')
const historyOpen = ref(false)
const historyLoading = ref(false)
const historyDetailError = ref('')
const historyDetail = ref(null)
const activeHistoryId = ref('')

const { job, elapsed, progress, isRunning, isSuccess, isFailed, isCancelled, track, cancel, reset: resetJob } = useJob()

const running = computed(() => isRunning.value)
const thresholdValid = computed(() => {
  const value = Number(state.threshold)
  return Number.isFinite(value) && value >= 0 && value <= 1
})
const singleClass = computed(() => {
  const info = state.sourceInfo
  return Boolean(info && (Number(info.pos) === 0 || Number(info.neg) === 0))
})
const modelDisplay = computed(() => {
  if (!state.sourceInfo) return '—'
  if (state.source?.kind === 'file') return state.sourceInfo.label || '外部预测结果'
  return state.sourceInfo.model_label || '—'
})
const canRun = computed(() =>
  Boolean(state.source && state.sourceInfo && state.metrics.length && thresholdValid.value) &&
  !running.value && !starting.value
)
const canSave = computed(() => {
  const name = state.saveName.trim()
  return Boolean(name) && name !== state.savedName
})
const plannedFigureText = computed(() => {
  if (!state.metrics.length) return '选择指标后将生成对应图表。'
  const figures = ['bar']
  if (state.metrics.includes('auc')) figures.push('roc')
  if (state.metrics.includes('ap')) figures.push('pr')
  if (state.metrics.some((item) => ['accuracy', 'precision', 'recall', 'f1', 'mcc'].includes(item))) figures.push('confusion')
  return `预计生成 ${figures.length} 张图`
})
const metricRows = computed(() =>
  Object.entries(result.value?.metrics || {}).map(([key, value]) => ({
    name: METRIC_LABEL[key] || key,
    value
  }))
)
const historyMetricRows = computed(() =>
  Object.entries(historyDetail.value?.metrics || {}).map(([key, value]) => ({
    name: METRIC_LABEL[key] || key,
    value
  }))
)

function thresholdText(value) {
  if (value === null || value === undefined) return '—'
  return Number(value).toFixed(2)
}

function summaryOf(metrics) {
  const entries = Object.entries(metrics || {}).slice(0, 3)
  if (!entries.length) return '—'
  return entries.map(([key, value]) => `${METRIC_LABEL[key] || key} ${formatPercent(value)}`).join(' · ')
}

function normalizeMetrics() {
  if (!singleClass.value) return
  state.metrics = state.metrics.filter((item) => !['auc', 'ap'].includes(item))
}

function toggleMetric(value, checked) {
  if (checked) {
    if (!state.metrics.includes(value)) state.metrics = [...state.metrics, value]
  } else {
    state.metrics = state.metrics.filter((item) => item !== value)
  }
}

function setMode(mode) {
  state.mode = mode
  if (mode === 'history') loadHistory()
}

async function loadDatasets() {
  try {
    const data = await listDatasets({ scope: 'mine', page_size: 100 })
    predictionDatasets.value = (data.items || []).filter((item) => item.source_type === 'prediction')
  } catch (error) {
    predictionDatasets.value = []
  }
}

function resetResult() {
  result.value = null
  state.result_ref = null
  state.job_id = null
  state.savedEvaluationId = null
  state.savedName = ''
  state.exportName = ''
  state.saveName = ''
  Object.keys(figureFailed).forEach((key) => delete figureFailed[key])
}

function applySource(source, info) {
  state.source = source
  state.sourceInfo = info
  resetResult()
  normalizeMetrics()
}

async function onDataset(id) {
  sourceError.value = ''
  if (!id) {
    if (state.source?.kind === 'dataset') {
      state.source = null
      state.sourceInfo = null
      resetResult()
    }
    return
  }
  if (state.source?.kind === 'file') {
    state.source = null
    state.sourceInfo = null
    resetResult()
  }
  try {
    const data = await evaluateApi.precheck(id)
    const item = predictionDatasets.value.find((entry) => entry.dataset_id === id)
    applySource(
      { kind: 'dataset', id, label: item?.name || id },
      { ...data, label: item?.name || id }
    )
  } catch (error) {
    sourceError.value = humanError(error)
    if (error?.code === 42201 || error?.code === 40001) {
      if (!unusableIds.value.includes(id)) unusableIds.value = [...unusableIds.value, id]
    }
    selectedDatasetId.value = ''
    state.source = null
    state.sourceInfo = null
    resetResult()
  }
}

async function onFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  importing.value = true
  sourceError.value = ''
  try {
    const data = await evaluateApi.importFile(file, state.importLabel.trim() || undefined)
    selectedDatasetId.value = ''
    applySource(
      { kind: 'file', id: data.file_id, label: data.label },
      { ...data }
    )
    state.exportName = `${data.label}-${shortId(data.file_id)}`
    state.saveName = `evaluate-${shortId(data.file_id)}`
  } catch (error) {
    sourceError.value = humanError(error)
  } finally {
    importing.value = false
  }
}

async function startEvaluate() {
  if (!canRun.value) return
  starting.value = true
  resetResult()
  try {
    const data = await evaluateApi.run({
      source: state.source,
      metrics: state.metrics,
      threshold: Number(state.threshold)
    })
    state.job_id = data.job_id
    track(data.job_id, data.total_figures)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    starting.value = false
  }
}

async function cancelJob() {
  try {
    await ElMessageBox.confirm('确认取消评估？本轮结果将被丢弃，不可导出与保存。', '取消评估', {
      type: 'warning',
      confirmButtonText: '取消评估',
      cancelButtonText: '继续等待'
    })
    await cancel()
    resetResult()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(humanError(error))
  }
}

async function loadResult(jobId) {
  const data = await evaluateApi.getResult(jobId)
  result.value = data
  state.result_ref = { job_id: jobId, kind: 'evaluate' }
  state.job_id = jobId
  const base = `evaluate-${shortId(jobId)}`
  if (!state.exportName) state.exportName = base
  if (!state.saveName) state.saveName = base
}

watch(
  () => job.value?.status,
  async (value) => {
    if (value === 'success' && job.value?.job_id) {
      try {
        await loadResult(job.value.job_id)
      } catch (error) {
        ElMessage.error(humanError(error))
      }
    } else if (value === 'failed' && job.value?.error_message) {
      ElMessage.error(job.value.error_message)
    } else if (value === 'cancelled') {
      resetResult()
    }
  }
)

watch(
  () => state.sourceInfo,
  () => normalizeMetrics(),
  { deep: true }
)

function retryFigure(key) {
  delete figureFailed[key]
  figureVersion.value += 1
}

function historyFigureSrc(type) {
  if (!historyDetail.value?.evaluation_id) return ''
  return evaluateApi.historyFigureUrl(historyDetail.value.evaluation_id, type)
}

async function downloadFigure(type) {
  if (!state.result_ref?.job_id) return
  downloadingFigure.value = type
  try {
    const response = await evaluateApi.figureBlob(state.result_ref.job_id, type)
    saveBlob(response, `${type}.png`)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    downloadingFigure.value = ''
  }
}

async function exportAs(format) {
  if (!state.result_ref?.job_id) return
  const filename = state.exportName.trim()
  if (!filename) {
    ElMessage.error('文件名不能为空')
    return
  }
  exporting.value = true
  try {
    const response = await evaluateApi.exportResult(state.result_ref.job_id, { filename, format })
    saveBlob(response, `${filename}.${format === 'excel' ? 'xlsx' : 'csv'}`)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    exporting.value = false
  }
}

async function saveEvaluation() {
  if (!state.result_ref?.job_id) return
  const name = state.saveName.trim()
  if (!name) return
  saving.value = true
  try {
    const data = await evaluateApi.saveHistory(state.result_ref.job_id, name)
    state.savedEvaluationId = data.evaluation_id
    state.savedName = name
    ElMessage.success('评估已保存到历史')
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    saving.value = false
  }
}

function resetHistoryPage() {
  history.page = 1
  loadHistory()
}

async function loadHistory() {
  history.loading = true
  history.error = ''
  try {
    const data = await evaluateApi.listHistory({
      q: historyQuery.value.trim() || undefined,
      page: history.page,
      page_size: history.page_size
    })
    history.items = data.items || []
    history.total = data.total
    history.page = data.page
  } catch (error) {
    history.error = humanError(error)
  } finally {
    history.loading = false
  }
}

function openHistory(row) {
  historyDetail.value = null
  historyDetailError.value = ''
  activeHistoryId.value = row.evaluation_id
  Object.keys(figureFailed)
    .filter((key) => key.startsWith('h-'))
    .forEach((key) => delete figureFailed[key])
  historyOpen.value = true
  historyLoading.value = true
  loadHistoryDetail(row.evaluation_id)
}

async function loadHistoryDetail(passedId) {
  const id = typeof passedId === 'string' ? passedId : activeHistoryId.value
  if (!id) {
    historyLoading.value = false
    return
  }
  activeHistoryId.value = id
  historyLoading.value = true
  historyDetailError.value = ''
  try {
    historyDetail.value = await evaluateApi.getHistory(id)
  } catch (error) {
    historyDetailError.value = humanError(error)
  } finally {
    historyLoading.value = false
  }
}

async function removeHistory(row) {
  try {
    await ElMessageBox.confirm(`确认删除评估「${row.name}」？删除后不可恢复。`, '删除评估', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  try {
    await evaluateApi.deleteHistory(row.evaluation_id)
    if (historyDetail.value?.evaluation_id === row.evaluation_id) historyOpen.value = false
    ElMessage.success('已删除')
    await loadHistory()
  } catch (error) {
    ElMessage.error(humanError(error))
  }
}

async function downloadHistoryFigure(type) {
  const id = historyDetail.value?.evaluation_id
  if (!id) return
  downloadingFigure.value = `h-${type}`
  try {
    const response = await evaluateApi.historyFigureBlob(id, type)
    saveBlob(response, `${type}.png`)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    downloadingFigure.value = ''
  }
}

async function exportHistoryAs(format) {
  const id = historyDetail.value?.evaluation_id
  if (!id) return
  const filename = historyDetail.value?.name || `evaluate-${shortId(id)}`
  exporting.value = true
  try {
    const response = await evaluateApi.exportHistory(id, { filename, format })
    saveBlob(response, `${filename}.${format === 'excel' ? 'xlsx' : 'csv'}`)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    exporting.value = false
  }
}

async function confirmReset() {
  try {
    await ElMessageBox.confirm('重置会清空本页进度与未保存结果，已保存的历史评估不受影响。', '重置页面', {
      type: 'warning',
      confirmButtonText: '重置',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  resetJob()
  selectedDatasetId.value = ''
  unusableIds.value = []
  sourceError.value = ''
  resetResult()
  await page.reset()
}

async function restore() {
  if (state.source?.kind === 'dataset') {
    selectedDatasetId.value = state.source.id
    try {
      const info = await evaluateApi.precheck(state.source.id)
      state.sourceInfo = { ...info, label: state.source.label }
    } catch (error) {
      sourceError.value = humanError(error)
      selectedDatasetId.value = ''
      state.source = null
      state.sourceInfo = null
    }
  }
  normalizeMetrics()
  const jobId = state.result_ref?.job_id
  if (!jobId) return
  try {
    const data = await getJob(jobId)
    if (data.status === 'success') {
      job.value = data
      await loadResult(jobId)
    } else if (['queued', 'running'].includes(data.status)) {
      state.job_id = data.job_id
      track(data.job_id, data.total)
    } else {
      resetResult()
    }
  } catch (error) {
    resetResult()
  }
}

onMounted(async () => {
  await page.ready
  await loadDatasets()
  await restore()
  if (state.mode === 'history') loadHistory()
})
</script>

<style scoped>
.seg {
  display: inline-flex;
  padding: 4px;
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 11px;
}

.seg-item {
  border: 0;
  background: transparent;
  color: var(--text-muted);
  font-weight: 650;
  font-size: 12.5px;
  padding: 7px 14px;
  border-radius: 8px;
  cursor: pointer;
}

.seg-item.active {
  background: var(--primary);
  color: white;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  font-size: 12.5px;
  font-weight: 650;
  color: var(--text-muted);
}

.hint {
  font-size: 12px;
  color: var(--text-soft);
  line-height: 1.55;
}

.form-error {
  color: var(--danger);
  font-size: 12.5px;
  margin-top: 8px;
}

.option {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.recognized {
  margin-top: 14px;
  padding: 12px;
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  border: 1px solid var(--border);
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}

.metric-item {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  padding: 10px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.metric-item.off {
  opacity: 0.6;
}

.metric-item .soft {
  font-size: 11.5px;
}

.threshold-row {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.threshold-row :deep(.el-slider) {
  flex: 1;
  min-width: 180px;
}

.result-grid {
  display: grid;
  grid-template-columns: minmax(0, 0.7fr) minmax(0, 1.3fr);
  gap: 16px;
}

.metric-table {
  align-self: start;
}

.figure-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.figure-card {
  margin: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  overflow: hidden;
}

.figure-card figcaption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-muted);
  font-size: 12.5px;
}

.figure-card img {
  display: block;
  width: 100%;
  height: auto;
  background: white;
}

.figure-failed {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 180px;
  color: var(--text-muted);
  font-size: 12.5px;
}

.export-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--border);
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.drawer {
  padding-bottom: 12px;
}

@media (max-width: 900px) {
  .result-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
