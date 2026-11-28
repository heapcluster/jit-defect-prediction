<template>
  <div class="stack">
    <PageHeader title="数据清洗" subtitle="确定性清洗与预处理，逐步观察数据变化" eyebrow="Pipeline 02">
      <template #actions>
        <el-button @click="confirmReset">重置</el-button>
      </template>
    </PageHeader>

    <div v-if="page.syncError" class="pill warning">进度未同步：{{ page.syncError }}</div>

    <SectionCard index="01" title="数据来源" description="支持本人数据集与 CSV / Excel；列结构与输入保持一致">
      <DataSourcePicker
        ref="pickerRef"
        :datasets="datasets"
        :import-api="cleanApi.importFile"
        :precheck-api="datasetPrecheck"
        mode="clean"
        :disabled="running"
        :initial-source="state.source"
        :initial-info="state.sourceInfo"
        @update:model-value="onSource"
        @validated="onValidated"
      />
    </SectionCard>

    <SectionCard index="02" title="清洗与预处理" description="至少选择一项；执行顺序可用箭头调整" :disabled="!state.source">
      <div class="ops">
        <div v-for="(item, index) in state.operations" :key="item.op" class="op" :class="{ off: !item.enabled }">
          <div class="op-head">
            <el-checkbox v-model="item.enabled" :disabled="running">{{ item.label }}</el-checkbox>
            <div class="row">
              <el-button link :disabled="running || index === 0" aria-label="上移" @click="move(index, -1)">↑</el-button>
              <el-button link :disabled="running || index === state.operations.length - 1" aria-label="下移" @click="move(index, 1)">↓</el-button>
            </div>
          </div>

          <div v-if="item.enabled" class="op-body">
            <template v-if="item.op === 'dedup'">
              <span class="label">方式</span>
              <el-select v-model="item.params.key" :disabled="running" style="width: 190px">
                <el-option label="完全重复行" value="full" />
                <el-option label="按提交 hash" value="commit_hash" />
              </el-select>
            </template>

            <template v-if="item.op === 'missing'">
              <span class="label">方式</span>
              <el-select v-model="item.params.mode" :disabled="running" style="width: 170px">
                <el-option label="删除含缺失行" value="drop" />
                <el-option label="均值填充" value="mean" />
                <el-option label="众数填充" value="mode" />
              </el-select>
              <span class="label">目标列</span>
              <el-select v-model="item.params.columns" multiple collapse-tags placeholder="全部允许列" :disabled="running" style="min-width: 200px">
                <el-option v-for="column in missingColumns" :key="column" :label="column" :value="column" />
              </el-select>
            </template>

            <template v-if="item.op === 'outlier'">
              <span class="label">方式</span>
              <el-select v-model="item.params.method" :disabled="running" style="width: 150px">
                <el-option label="IQR 截断" value="iqr_clip" />
                <el-option label="IQR 删除" value="iqr_drop" />
              </el-select>
              <span class="label">系数</span>
              <el-input-number v-model="item.params.factor" :min="0.1" :max="10" :step="0.1" :controls="false" :disabled="running" style="width: 100px" />
              <span class="label">目标列</span>
              <el-select v-model="item.params.columns" multiple collapse-tags placeholder="全部专家特征" :disabled="running" style="min-width: 200px">
                <el-option v-for="column in outlierColumns" :key="column" :label="column" :value="column" />
              </el-select>
            </template>

            <template v-if="item.op === 'label'">
              <span class="muted">仅保留 bug ∈ {0, 1} 的行。</span>
            </template>

            <template v-if="item.op === 'balance'">
              <span class="label">方式</span>
              <el-select v-model="item.params.method" :disabled="running" style="width: 150px">
                <el-option label="欠采样" value="under" />
              </el-select>
              <span class="label">比例</span>
              <el-input-number v-model="item.params.ratio" :min="1" :max="20" :step="0.5" :controls="false" :disabled="running" style="width: 100px" />
              <span class="muted">多数类保留到少数类的 ratio 倍。</span>
            </template>
          </div>
        </div>
      </div>

      <template #footer>
        <span v-if="!enabledOps.length" class="muted">至少选择一项清洗操作。</span>
        <span v-else class="muted">将按 {{ enabledOps.length }} 个步骤顺序执行。</span>
        <el-button type="primary" :disabled="!canRun" :loading="starting" @click="startClean">开始清洗</el-button>
      </template>
    </SectionCard>

    <SectionCard v-if="job" index="03" title="执行与变化" description="每一步统计来自后端，图表与统计表一致">
      <JobPanel
        :job="job"
        :elapsed="elapsed"
        :progress="progress"
        :is-running="isRunning"
        :is-success="isSuccess"
        :is-failed="isFailed"
        @cancel="cancelJob"
      />
      <div v-if="steps.length" class="steps">
        <div v-for="step in steps" :key="step.op" class="step">
          <div class="step-head">
            <strong>{{ labelOf(step.op) }}</strong>
            <span class="mono muted">{{ step.before }} → {{ step.after }}</span>
            <span v-if="step.changed === 0" class="pill">无变化</span>
            <span v-else class="pill danger">减少 {{ step.changed }}</span>
          </div>
          <div v-if="step.changed > 0" class="bars">
            <div class="bar-row"><span>前</span><div class="bar"><i :style="{ width: barWidth(step.before) }" /></div></div>
            <div class="bar-row"><span>后</span><div class="bar"><i class="after" :style="{ width: barWidth(step.after) }" /></div></div>
          </div>
        </div>
      </div>
      <div v-if="steps.length" class="stats-table">
        <table>
          <thead><tr><th>步骤</th><th>前</th><th>后</th><th>正 / 负</th></tr></thead>
          <tbody>
            <tr v-for="step in steps" :key="`s-${step.op}`">
              <td>{{ labelOf(step.op) }}</td>
              <td class="num">{{ step.before }}</td>
              <td class="num">{{ step.after }}</td>
              <td class="num">{{ step.stats.pos }} / {{ step.stats.neg }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </SectionCard>

    <SectionCard v-if="result" index="04" title="清洗结果" description="列结构与输入完全一致">
      <template #aside>
        <span class="pill success">正 {{ summary.pos }}</span>
        <span class="pill">负 {{ summary.neg }}</span>
        <span class="pill">{{ summary.total }} 行</span>
      </template>

      <el-table v-loading="rowsLoading" :data="rows" border>
        <el-table-column v-for="column in result.columns" :key="column" :prop="column" :label="column" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <span :class="{ mono: column === 'commit_id' }">{{ cell(row[column], column) }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination
          v-model:current-page="rowPage"
          :page-size="rowPageSize"
          :total="summary.total"
          layout="prev, pager, next"
          :hide-on-single-page="true"
          @current-change="loadRows"
        />
      </div>

      <div class="export-row">
        <el-input v-model="exportName" placeholder="导出文件名（不含扩展名）" style="max-width: 260px" />
        <el-radio-group v-model="exportFormat">
          <el-radio value="csv">CSV</el-radio>
          <el-radio value="excel">Excel</el-radio>
        </el-radio-group>
        <el-button :loading="exporting" @click="doExport">导出</el-button>
      </div>

      <template #footer>
        <div class="row wrap grow">
          <span class="muted">保存后可在数据存储页复用；覆盖保存不改变已有模型与预测。</span>
          <el-input v-model="state.datasetName" placeholder="数据集名称" style="max-width: 240px" :disabled="state.saved" />
        </div>
        <div class="row">
          <span v-if="state.saved" class="pill success">已保存</span>
          <el-button type="primary" :loading="saving" :disabled="state.saved || !state.datasetName.trim()" @click="saveDataset">
            保存到数据库
          </el-button>
        </div>
      </template>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import SectionCard from '../components/SectionCard.vue'
import JobPanel from '../components/JobPanel.vue'
import DataSourcePicker from '../components/DataSourcePicker.vue'
import { saveDataset as saveDatasetApi, getDataset, listDatasets } from '../api/datasets'
import * as cleanApi from '../api/clean'
import { getJob } from '../api/jobs'
import { humanError } from '../utils/format'
import { saveBlob } from '../utils/download'
import { useJob } from '../composables/useJob'
import { usePageState } from '../composables/usePageState'

const OP_LABEL = {
  dedup: '去重',
  missing: '缺失值',
  outlier: '异常值',
  label: '标签规范化',
  balance: '样本平衡'
}

function defaults() {
  return {
    step: 1,
    source: null,
    sourceInfo: null,
    operations: [
      { op: 'dedup', label: '去重', enabled: true, params: { key: 'full' } },
      { op: 'missing', label: '缺失值', enabled: false, params: { mode: 'drop', columns: [] } },
      { op: 'outlier', label: '异常值', enabled: false, params: { method: 'iqr_clip', factor: 1.5, columns: [] } },
      { op: 'label', label: '标签规范化', enabled: true, params: {} },
      { op: 'balance', label: '样本平衡', enabled: false, params: { method: 'under', ratio: 1 } }
    ],
    job_id: null,
    result_ref: null,
    datasetName: '',
    saved: false
  }
}

const page = usePageState('clean', defaults)
const state = page.state
const datasets = ref([])
const pickerRef = ref(null)
const steps = ref([])
const rows = ref([])
const resultColumns = ref([])
const summary = reactive({ total: 0, pos: 0, neg: 0 })
const rowsLoading = ref(false)
const rowPage = ref(1)
const rowPageSize = 20
const starting = ref(false)
const exportName = ref('')
const exportFormat = ref('csv')
const exporting = ref(false)
const saving = ref(false)

const { job, elapsed, progress, isRunning, isSuccess, isFailed, track, cancel, reset: resetJob } = useJob()

const running = computed(() => isRunning.value)
const result = computed(() =>
  state.result_ref ? { job_id: state.result_ref.job_id, columns: resultColumns.value } : null
)
const enabledOps = computed(() => state.operations.filter((item) => item.enabled))
const canRun = computed(() => state.source && enabledOps.value.length > 0 && !running.value && !starting.value)

const missingColumns = computed(() => {
  const columns = state.sourceInfo?.columns || []
  const meta = ['project', 'commit_id', 'commit_time', 'author_name', 'author_email', 'commit_message', 'bug']
  if (state.sourceInfo?.line === 'expert') {
    return columns.length ? columns : meta
  }
  return meta
})

const outlierColumns = computed(() => {
  const columns = state.sourceInfo?.columns || []
  return columns.filter((column) => !['project', 'commit_id', 'commit_time', 'author_name', 'author_email', 'commit_message', 'bug'].includes(column))
})

function labelOf(op) {
  return OP_LABEL[op] || op
}

async function datasetPrecheck(id) {
  return getDataset(id, { page: 1, page_size: 1 })
}

async function loadDatasets() {
  try {
    const data = await listDatasets({ scope: 'mine', page_size: 100 })
    datasets.value = data.items.filter((item) => ['git_repo', 'upload', 'clean'].includes(item.source_type))
  } catch (error) {
    datasets.value = []
  }
}

function onSource(value) {
  state.source = value
  if (!value) {
    state.sourceInfo = null
    state.result_ref = null
    state.job_id = null
    resultColumns.value = []
    state.saved = false
  }
}

function onValidated(info) {
  state.sourceInfo = info
  state.result_ref = null
  state.job_id = null
  resultColumns.value = []
  if (info && !state.datasetName) state.datasetName = `${info.label}-cleaned`
  if (info && !exportName.value) exportName.value = `${info.label}-cleaned`
}

function move(index, offset) {
  const target = index + offset
  if (target < 0 || target >= state.operations.length) return
  const list = [...state.operations]
  ;[list[index], list[target]] = [list[target], list[index]]
  state.operations = list
}

async function startClean() {
  if (!canRun.value) return
  starting.value = true
  state.result_ref = null
  state.job_id = null
  resultColumns.value = []
  state.saved = false
  steps.value = []
  rows.value = []
  const operations = state.operations
    .filter((item) => item.enabled)
    .map((item) => ({ op: item.op, params: item.params }))
  try {
    const data = await cleanApi.run({ source: state.source, operations })
    state.job_id = data.job_id
    state.step = 3
    track(data.job_id, operations.length)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    starting.value = false
  }
}

async function cancelJob() {
  try {
    await ElMessageBox.confirm('确认取消当前清洗任务？本轮未保存结果将被丢弃。', '取消任务', {
      type: 'warning',
      confirmButtonText: '取消任务',
      cancelButtonText: '继续等待'
    })
    await cancel()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(humanError(error))
  }
}

async function loadSteps() {
  if (!state.result_ref?.job_id) return
  try {
    const data = await cleanApi.getSteps(state.result_ref.job_id)
    steps.value = data.steps || []
  } catch (error) {
    steps.value = []
  }
}

async function loadRows() {
  if (!state.result_ref?.job_id) return
  rowsLoading.value = true
  try {
    const data = await cleanApi.getRows(state.result_ref.job_id, { page: rowPage.value, page_size: rowPageSize })
    rows.value = data.items
    resultColumns.value = data.columns
    Object.assign(summary, data.summary)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    rowsLoading.value = false
  }
}

function barWidth(value) {
  const max = Math.max(...steps.value.map((step) => step.before), 1)
  return `${Math.max(4, Math.round((value / max) * 100))}%`
}

function cell(value, column) {
  if (value === null || value === undefined || value === '') return '—'
  if (column === 'bug') return Number(value) === 1 ? '缺陷' : '正常'
  if (typeof value === 'number') return Number(value.toFixed(4))
  return String(value)
}

watch(
  () => job.value?.status,
  (value) => {
    if (value !== 'success' || !job.value?.job_id) return
    state.job_id = job.value.job_id
    state.result_ref = { job_id: job.value.job_id, kind: 'clean' }
    state.step = 3
    resultColumns.value = []
    rowPage.value = 1
    loadSteps()
    loadRows()
  }
)

async function doExport() {
  if (!state.result_ref?.job_id) return
  if (!exportName.value.trim()) {
    ElMessage.error('文件名不能为空')
    return
  }
  exporting.value = true
  try {
    const response = await cleanApi.exportResult(state.result_ref.job_id, {
      filename: exportName.value.trim(),
      format: exportFormat.value
    })
    saveBlob(response, `${exportName.value.trim()}.${exportFormat.value === 'excel' ? 'xlsx' : 'csv'}`)
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    exporting.value = false
  }
}

async function saveDataset() {
  if (!state.result_ref?.job_id) return
  saving.value = true
  try {
    await saveDatasetApi(state.result_ref.job_id, state.datasetName.trim())
    state.saved = true
    ElMessage.success('数据集已保存')
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
  steps.value = []
  rows.value = []
  Object.assign(summary, { total: 0, pos: 0, neg: 0 })
  await page.reset()
}

async function restore() {
  if (!state.result_ref?.job_id) return
  try {
    const data = await getJob(state.result_ref.job_id)
    if (data.status === 'success') {
      job.value = data
      state.job_id = data.job_id
      state.result_ref = { job_id: data.job_id, kind: 'clean' }
      resultColumns.value = []
      await loadSteps()
      await loadRows()
    } else if (['queued', 'running'].includes(data.status)) {
      state.job_id = data.job_id
      track(data.job_id, data.total)
    } else {
      state.result_ref = null
      state.job_id = null
    }
  } catch (error) {
    state.result_ref = null
    state.job_id = null
  }
}

onMounted(async () => {
  await page.ready
  await loadDatasets()
  await restore()
})
</script>

<style scoped>
.ops {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.op {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-muted);
  padding: 12px 14px;
}

.op.off {
  opacity: 0.7;
}

.op-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.op-body {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border);
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
}

.steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.step {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  background: var(--surface);
}

.step-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.bars {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-row {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  color: var(--text-soft);
}

.bar {
  height: 8px;
  border-radius: 999px;
  background: #eef2f8;
  overflow: hidden;
}

.bar i {
  display: block;
  height: 100%;
  background: #93c5fd;
  border-radius: 999px;
}

.bar i.after {
  background: var(--primary);
}

.stats-table {
  margin-top: 14px;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

th,
td {
  border-bottom: 1px solid var(--border);
  padding: 8px 10px;
  text-align: left;
}

th {
  color: var(--text-muted);
  font-weight: 600;
  background: var(--surface-muted);
}

.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
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
</style>
