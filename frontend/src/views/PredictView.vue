<template>
  <div class="stack">
    <PageHeader title="模型预测" subtitle="选择数据与模型，批量预测缺陷风险" eyebrow="Pipeline 04">
      <template #actions>
        <el-button @click="confirmReset">重置</el-button>
      </template>
    </PageHeader>

    <div v-if="page.syncError" class="pill warning">进度未同步：{{ page.syncError }}</div>

    <SectionCard index="01" title="选择数据" description="收集 / 清洗 / 导入清洗 / 测试集，或符合字段契约的文件">
      <DataSourcePicker
        ref="pickerRef"
        :datasets="datasets"
        :import-api="predictApi.importFile"
        :precheck-api="predictApi.precheck"
        mode="predict"
        :disabled="running"
        :initial-source="state.source"
        :initial-info="state.sourceInfo"
        @update:model-value="onSource"
        @validated="onValidated"
      />
      <p class="note">说明：可选收集、清洗、导入清洗与测试集；外部导入的数据集不提供缺陷定位。</p>
    </SectionCard>

    <SectionCard
      index="02"
      title="选择模型"
      description="已保存模型按数据线过滤，导入模型需要声明模型线"
      :disabled="!state.sourceInfo"
    >
      <div class="grid-2">
        <div class="field">
          <label class="field-label" for="saved-model">已保存模型</label>
          <el-select
            id="saved-model"
            :model-value="state.model?.kind === 'saved' ? state.model.model_name : ''"
            filterable
            clearable
            placeholder="请选择与数据线一致的模型"
            :disabled="running"
            style="width: 100%"
            @change="onSavedModel"
          >
            <el-option v-for="item in models" :key="item.id" :value="item.id" :label="item.name">
              <div class="option">
                <span class="mono">{{ item.name }}</span>
                <span class="soft">{{ item.algo || '—' }} · {{ (item.format || '').toUpperCase() || '—' }}</span>
              </div>
            </el-option>
          </el-select>
          <div v-if="!models.length" class="hint">当前数据线下还没有可用模型，可先在训练页保存，或在右侧导入模型。</div>
        </div>

        <div class="field">
          <label class="field-label">导入模型</label>
          <div class="row wrap">
            <el-select v-model="importLine" :disabled="running" style="width: 130px">
              <el-option label="专家特征" value="expert" />
              <el-option label="语义向量" value="semantic" />
            </el-select>
            <input ref="modelInput" type="file" accept=".pkl,.pt" hidden @change="onModelFile" />
            <el-button :loading="importing" :disabled="running" @click="modelInput?.click()">选择模型文件</el-button>
          </div>
          <div class="hint">支持 `.pkl`（sklearn）与本项目导出的 `.pt`；.pt 必须带自包含格式标记。外部模型存在加载风险，请确认来源可信。</div>
          <div v-if="importError" class="form-error">{{ importError }}</div>
          <div v-if="state.modelInfo" class="import-card">
            <div class="row wrap">
              <span class="pill primary">{{ LINE[state.modelInfo.line] || state.modelInfo.line }}</span>
              <span class="pill">{{ state.modelInfo.n_features ?? '—' }} 维</span>
              <span class="pill">{{ (state.modelInfo.framework || '').toUpperCase() || '—' }}</span>
              <span class="pill">{{ (state.modelInfo.format || '').toUpperCase() || '—' }}</span>
            </div>
            <div class="row-between">
              <span class="mono soft">{{ state.modelInfo.label }}</span>
              <span v-if="state.modelInfo.savedName" class="pill success">已保存 {{ state.modelInfo.savedName }}</span>
              <el-button
                v-else
                size="small"
                :loading="savingModel"
                :disabled="running"
                @click="saveImportedModel"
              >
                保存为模型资产
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="modelMismatch" class="form-error">模型线（{{ LINE[modelLine] || modelLine }}）与数据线（{{ LINE[state.sourceInfo?.line] || state.sourceInfo?.line }}）不一致，请重新选择模型。</div>
      <div v-if="state.model" class="selected-model">
        <span class="pill primary">已选</span>
        <span class="mono">{{ state.model.kind === 'saved' ? state.model.model_name : state.model.label }}</span>
        <span class="muted">｜ {{ LINE[modelLine] || modelLine || '—' }} ｜ 特征数 {{ featureCount }}</span>
      </div>
    </SectionCard>

    <SectionCard
      index="03"
      title="概率阈值"
      description="概率 ≥ 阈值判为缺陷"
      :disabled="!state.sourceInfo || !modelReady"
    >
      <div class="threshold-row">
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
      </div>
      <p v-if="!thresholdValid" class="form-error">阈值必须位于 0–1。</p>
    </SectionCard>

    <SectionCard index="04" title="执行预测" description="运行中锁定上游；取消后结果清空且不可保存">
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
      <div v-else class="muted">开始预测后，这里显示进度、当前阶段与耗时。</div>
      <template #footer>
        <span class="muted">{{ selectedSummary }}</span>
        <el-button type="primary" :disabled="!canRun" :loading="starting" @click="startPredict">开始预测</el-button>
      </template>
    </SectionCard>

    <SectionCard v-if="hasResult" index="05" title="预测结果" description="点击任意行进入预测详情，查看解释与缺陷定位">
      <template #aside>
        <span class="pill">{{ resultTotal }} 行</span>
        <el-select v-model="state.resultFilter" size="small" style="width: 110px" @change="onFilter">
          <el-option label="全部" value="all" />
          <el-option label="缺陷" value="defect" />
          <el-option label="正常" value="normal" />
        </el-select>
      </template>

      <div v-if="rowsError">
        <ErrorState :message="rowsError" @retry="loadRows" />
      </div>
      <template v-else>
        <el-table
          v-loading="rowsLoading"
          :data="rows"
          border
          class="result-table"
          @row-click="openRow"
        >
          <el-table-column label="提交哈希" width="150">
            <template #default="{ row }"><span class="mono">{{ maskHash(row.commit_hash, 10) }}</span></template>
          </el-table-column>
          <el-table-column prop="commit_message" label="提交说明" min-width="240" show-overflow-tooltip />
          <el-table-column prop="author_name" label="作者" width="120" show-overflow-tooltip />
          <el-table-column label="提交时间" width="176">
            <template #default="{ row }">{{ formatTime(row.commit_time) }}</template>
          </el-table-column>
          <el-table-column label="真实标签" width="104" align="center">
            <template #default="{ row }">
              <span v-if="row.bug === null || row.bug === undefined" class="soft">—</span>
              <span v-else class="pill" :class="row.bug === 1 ? 'danger' : 'success'">{{ row.bug === 1 ? '缺陷' : '正常' }}</span>
            </template>
          </el-table-column>
          <el-table-column label="预测概率" width="110" align="right">
            <template #default="{ row }">{{ Number(row.risk_score).toFixed(4) }}</template>
          </el-table-column>
          <el-table-column label="预测结果" width="104" align="center">
            <template #default="{ row }">
              <span class="pill" :class="row.predicted_label === 1 ? 'danger' : 'success'">
                {{ row.predicted_label === 1 ? '缺陷' : '正常' }}
              </span>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            v-model:current-page="state.resultPage"
            :page-size="pageSize"
            :total="resultTotal"
            layout="total, prev, pager, next"
            :hide-on-single-page="true"
            @current-change="loadRows"
          />
        </div>

        <div class="export-row">
          <el-input v-model="state.exportName" placeholder="导出文件名（不含扩展名）" style="max-width: 280px" />
          <el-button :loading="exporting" @click="exportAs('csv')">导出 CSV</el-button>
          <el-button :loading="exporting" @click="exportAs('excel')">导出 Excel</el-button>
        </div>
      </template>

      <template #footer>
        <div class="row wrap grow">
          <span class="muted">保存后可在数据存储页复用；每次保存独立成条，不覆盖历史。</span>
          <el-input v-model="state.saveName" placeholder="预测数据集名称" style="max-width: 260px" />
        </div>
        <div class="row">
          <span v-if="state.savedDatasetId" class="pill success">已保存 {{ state.savedDatasetId }}</span>
          <el-button type="primary" :loading="saving" :disabled="!state.saveName.trim()" @click="saveResult">
            保存到数据库
          </el-button>
        </div>
      </template>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import SectionCard from '../components/SectionCard.vue'
import JobPanel from '../components/JobPanel.vue'
import DataSourcePicker from '../components/DataSourcePicker.vue'
import ErrorState from '../components/ErrorState.vue'
import { listDatasets } from '../api/datasets'
import { listFiles } from '../api/storage'
import { getJob } from '../api/jobs'
import * as predictApi from '../api/predict'
import { humanError, LINE, maskHash, formatTime, shortId } from '../utils/format'
import { saveBlob } from '../utils/download'
import { useJob } from '../composables/useJob'
import { usePageState } from '../composables/usePageState'

const pageSize = 20

function defaults() {
  return {
    step: 1,
    source: null,
    sourceInfo: null,
    model: null,
    modelInfo: null,
    threshold: 0.5,
    job_id: null,
    result_ref: null,
    resultPage: 1,
    resultFilter: 'all',
    exportName: '',
    saveName: '',
    savedDatasetId: null
  }
}

const router = useRouter()
const page = usePageState('predict', defaults)
const state = page.state
const datasets = ref([])
const models = ref([])
const pickerRef = ref(null)
const modelInput = ref(null)
const importLine = ref('expert')
const importing = ref(false)
const importError = ref('')
const savingModel = ref(false)
const starting = ref(false)
const rows = ref([])
const rowsLoading = ref(false)
const rowsError = ref('')
const resultTotal = ref(0)
const exporting = ref(false)
const saving = ref(false)

const { job, elapsed, progress, isRunning, isSuccess, isFailed, isCancelled, track, cancel, reset: resetJob } = useJob()

const running = computed(() => isRunning.value)
const hasResult = computed(() => Boolean(state.result_ref?.job_id))
const thresholdValid = computed(() => {
  const value = Number(state.threshold)
  return Number.isFinite(value) && value >= 0 && value <= 1
})
const modelLine = computed(() => state.modelInfo?.line || state.model?.line || '')
const modelMismatch = computed(() =>
  Boolean(state.model && state.sourceInfo && modelLine.value && modelLine.value !== state.sourceInfo.line)
)
const modelReady = computed(() => Boolean(state.model) && !modelMismatch.value)
const featureCount = computed(() => {
  if (state.modelInfo?.n_features) return state.modelInfo.n_features
  return state.sourceInfo?.line === 'semantic' ? 768 : 14
})
const canRun = computed(() =>
  Boolean(state.source && state.sourceInfo && modelReady.value && thresholdValid.value) &&
  !running.value && !starting.value
)
const selectedSummary = computed(() => {
  const line = LINE[state.sourceInfo?.line] || '—'
  const model = state.model
    ? state.model.kind === 'saved'
      ? state.model.model_name
      : state.model.label
    : '未选择模型'
  return `${line} ｜ ${model} ｜ 阈值 ${Number(state.threshold || 0).toFixed(2)}`
})

function modelPayload() {
  if (!state.model) return null
  if (state.model.kind === 'saved') return { kind: 'saved', name: state.model.model_name }
  return {
    kind: 'uploaded',
    model_ref: state.model.model_ref,
    line: state.model.line,
    label: state.model.label
  }
}

function resetResult() {
  state.result_ref = null
  state.job_id = null
  state.resultPage = 1
  state.savedDatasetId = null
  rows.value = []
  resultTotal.value = 0
  rowsError.value = ''
}

function onSource(value) {
  state.source = value
  if (!value) {
    state.sourceInfo = null
    resetResult()
  }
}

function onValidated(info) {
  state.sourceInfo = info
  resetResult()
  importLine.value = info?.line || 'expert'
  state.exportName = ''
  state.saveName = ''
}

async function loadDatasets() {
  try {
    const data = await listDatasets({ scope: 'mine', page_size: 100 })
    datasets.value = data.items.filter((item) =>
      ['git_repo', 'upload', 'clean', 'split'].includes(item.source_type)
    )
  } catch (error) {
    datasets.value = []
  }
}

async function loadModels(line) {
  if (!line) {
    models.value = []
    return
  }
  try {
    const data = await listFiles({ type: 'model', line, page_size: 100 })
    models.value = (data.items || []).filter((item) => item.status === 'available')
  } catch (error) {
    models.value = []
  }
}

function onSavedModel(name) {
  if (!name) {
    if (state.model?.kind === 'saved') {
      state.model = null
      state.modelInfo = null
    }
    return
  }
  const item = models.value.find((entry) => entry.id === name)
  state.model = {
    kind: 'saved',
    model_name: name,
    model_ref: null,
    label: name,
    line: item?.badge || state.sourceInfo?.line || 'expert'
  }
  state.modelInfo = {
    label: name,
    line: item?.badge || state.sourceInfo?.line || 'expert',
    n_features: null,
    framework: item?.framework || null,
    format: item?.format || null,
    savedName: name
  }
  importError.value = ''
}

async function onModelFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  importing.value = true
  importError.value = ''
  try {
    const data = await predictApi.importModel(file, importLine.value)
    state.model = {
      kind: 'uploaded',
      model_name: null,
      model_ref: data.model_ref,
      label: data.label,
      line: data.line
    }
    state.modelInfo = { ...data, savedName: null }
  } catch (error) {
    importError.value = humanError(error)
  } finally {
    importing.value = false
  }
}

async function saveImportedModel() {
  if (!state.modelInfo?.model_ref) return
  savingModel.value = true
  try {
    const data = await predictApi.saveModel({
      model_ref: state.modelInfo.model_ref,
      name: state.modelInfo.label
    })
    state.modelInfo = { ...state.modelInfo, savedName: data.model_name }
    state.model = {
      kind: 'saved',
      model_name: data.model_name,
      model_ref: null,
      label: data.model_name,
      line: state.modelInfo.line
    }
    ElMessage.success('模型已保存，可用于后续解释')
    await loadModels(state.modelInfo.line)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    savingModel.value = false
  }
}

async function startPredict() {
  if (!canRun.value) return
  starting.value = true
  resetResult()
  try {
    const data = await predictApi.run({
      source: state.source,
      model: modelPayload(),
      threshold: Number(state.threshold)
    })
    state.job_id = data.job_id
    track(data.job_id, data.total)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    starting.value = false
  }
}

async function cancelJob() {
  try {
    await ElMessageBox.confirm('确认取消预测？本轮结果将被丢弃，不可保存。', '取消预测', {
      type: 'warning',
      confirmButtonText: '取消预测',
      cancelButtonText: '继续等待'
    })
    await cancel()
    resetResult()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(humanError(error))
  }
}

async function onJobSuccess() {
  const jobId = job.value?.job_id
  if (!jobId) return
  if (state.result_ref?.job_id === jobId && rows.value.length) return
  state.result_ref = { job_id: jobId, kind: 'predict' }
  state.job_id = jobId
  state.resultPage = 1
  const base = state.model?.kind === 'saved'
    ? state.model.model_name.replace(/^[a-z]+-/, '')
    : state.model?.label || 'predict'
  if (!state.exportName) state.exportName = `${base}-${shortId(jobId)}`
  if (!state.saveName) state.saveName = `${base}-${shortId(jobId)}`
  await loadRows()
}

watch(
  () => job.value?.status,
  async (value) => {
    if (value === 'success') {
      await onJobSuccess()
    } else if (value === 'failed' && job.value?.error_message) {
      ElMessage.error(job.value.error_message)
    } else if (value === 'cancelled') {
      resetResult()
    }
  }
)

watch(
  () => state.sourceInfo?.line,
  (line) => {
    if (!line) return
    importLine.value = line
    loadModels(line)
  }
)

async function loadRows() {
  const jobId = state.result_ref?.job_id
  if (!jobId) return
  rowsLoading.value = true
  rowsError.value = ''
  try {
    const data = await predictApi.getRows(jobId, {
      page: state.resultPage,
      page_size: pageSize,
      result: state.resultFilter
    })
    rows.value = data.items
    resultTotal.value = data.total
    state.resultPage = data.page
  } catch (error) {
    rowsError.value = humanError(error)
  } finally {
    rowsLoading.value = false
  }
}

function onFilter() {
  state.resultPage = 1
  loadRows()
}

function openRow(row) {
  if (!state.result_ref?.job_id) return
  router.push(`/predict/${state.result_ref.job_id}/commit/${row.commit_hash}`)
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
    const response = await predictApi.exportResult(state.result_ref.job_id, { filename, format })
    saveBlob(response, `${filename}.${format === 'excel' ? 'xlsx' : 'csv'}`)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    exporting.value = false
  }
}

async function saveResult() {
  const jobId = state.result_ref?.job_id
  if (!jobId) return
  const name = state.saveName.trim()
  if (!name) return
  saving.value = true
  try {
    const data = await predictApi.saveResult(jobId, name)
    state.savedDatasetId = data.dataset_id
    ElMessage.success('预测结果已保存')
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    saving.value = false
  }
}

async function confirmReset() {
  try {
    await ElMessageBox.confirm('重置会清空本页进度与未保存结果，已保存资产不受影响。', '重置页面', {
      type: 'warning',
      confirmButtonText: '重置',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  resetJob()
  pickerRef.value?.reset()
  models.value = []
  resetResult()
  await page.reset()
}

async function restore() {
  if (state.sourceInfo?.line) {
    importLine.value = state.sourceInfo.line
    await loadModels(state.sourceInfo.line)
  }
  const jobId = state.result_ref?.job_id
  if (!jobId) return
  try {
    const data = await getJob(jobId)
    if (data.status === 'success') {
      job.value = data
      await loadRows()
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
})
</script>

<style scoped>
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

.note {
  margin-top: 12px;
  font-size: 12.5px;
  color: var(--text-soft);
}

.hint {
  font-size: 12px;
  color: var(--text-soft);
  line-height: 1.55;
}

.form-error {
  color: var(--danger);
  font-size: 12.5px;
  margin-top: 10px;
}

.option {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.import-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.selected-model {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12.5px;
}

.threshold-row {
  display: flex;
  align-items: center;
  gap: 18px;
}

.threshold-row :deep(.el-slider) {
  flex: 1;
  min-width: 160px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.export-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--border);
}

.result-table :deep(.el-table__row) {
  cursor: pointer;
}

@media (max-width: 768px) {
  .threshold-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
