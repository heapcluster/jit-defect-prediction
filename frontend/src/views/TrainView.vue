<template>
  <div class="stack">
    <PageHeader title="模型训练" subtitle="选择数据与算法，切分训练 / 验证 / 测试并对比模型" eyebrow="Pipeline 03">
      <template #actions>
        <el-button @click="confirmReset">重置</el-button>
      </template>
    </PageHeader>

    <div v-if="page.syncError" class="pill warning">进度未同步：{{ page.syncError }}</div>

    <SectionCard index="01" title="选择数据" description="收集 / 清洗 / 导入清洗结果，或符合字段契约的文件">
      <DataSourcePicker
        ref="pickerRef"
        :datasets="datasets"
        :import-api="trainApi.importFile"
        :precheck-api="trainApi.precheck"
        mode="train"
        :disabled="running"
        :initial-source="state.source"
        :initial-info="state.sourceInfo"
        @update:model-value="onSource"
        @validated="onValidated"
      />
    </SectionCard>

    <SectionCard index="02" title="选择算法" description="只列当前模型线的算法，默认全部不勾选" :disabled="!state.sourceInfo">
      <AlgorithmEditor
        v-model="state.algorithms"
        :algorithms="algorithms"
        :disabled="running"
      />
      <div v-if="algoError" class="form-error">{{ algoError }}</div>
    </SectionCard>

    <SectionCard index="03" title="切分数据" description="时间序按提交时间升序，比例固定随机种子 42" :disabled="!state.sourceInfo">
      <div class="split">
        <el-radio-group v-model="state.split.mode" :disabled="running">
          <el-radio-button value="time">时间序</el-radio-button>
          <el-radio-button value="random">随机比例</el-radio-button>
        </el-radio-group>
        <div class="ratio-row">
          <label>训练 <el-input-number v-model="state.split.ratios.train" :min="1" :max="98" :controls="false" :disabled="running" /> %</label>
          <label>验证 <el-input-number v-model="state.split.ratios.valid" :min="1" :max="98" :controls="false" :disabled="running" /> %</label>
          <label>测试 <el-input-number v-model="state.split.ratios.test" :min="1" :max="98" :controls="false" :disabled="running" /> %</label>
          <span class="pill" :class="ratioTotal === 100 ? 'success' : 'danger'">合计 {{ ratioTotal }}%</span>
        </div>
        <div class="preview">
          <span>预览</span>
          <strong>训练 {{ splitPreview.train }}</strong>
          <strong>验证 {{ splitPreview.valid }}</strong>
          <strong>测试 {{ splitPreview.test }}</strong>
          <span class="soft">行数按 floor 计算</span>
        </div>
        <p v-if="ratioTotal !== 100" class="form-error">三段比例必须为正且合计 100%。</p>
      </div>
    </SectionCard>

    <SectionCard index="04" title="执行训练" description="运行中锁定上游；单个算法失败不阻断其余算法">
      <div v-if="job">
        <JobPanel
          :job="job"
          :elapsed="elapsed"
          :progress="progress"
          :is-running="isRunning"
          :is-success="isSuccess"
          :is-failed="isFailed"
          @cancel="cancelJob"
        />
        <el-table v-if="algorithmStatus.length" :data="algorithmStatus" size="small" border class="job-table">
          <el-table-column prop="algo" label="算法" width="120" />
          <el-table-column prop="state" label="状态" width="120">
            <template #default="{ row }">
              <span class="pill" :class="row.done ? 'success' : row.running ? 'warning' : ''">
                {{ row.done ? '完成' : row.running ? '运行中' : '等待' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="stage" label="阶段" />
        </el-table>
      </div>
      <div v-else class="muted">开始训练后，这里显示进度、当前模型与耗时。</div>
      <template #footer>
        <span class="muted">{{ selectedCount }} 个算法已选择 ｜ 当前 {{ lineLabel }}</span>
        <el-button type="primary" :disabled="!canRun" :loading="starting" @click="startTrain">开始训练</el-button>
      </template>
    </SectionCard>

    <SectionCard v-if="result" index="05" title="训练结果" description="指标为训练 / 验证两段；缺类指标显示 —">
      <template #aside>
        <span class="pill">{{ result.split_counts?.train ?? 0 }} / {{ result.split_counts?.valid ?? 0 }} / {{ result.split_counts?.test ?? 0 }}</span>
      </template>

      <div class="result-grid">
        <div class="table-wrap">
          <el-table :data="successModels" border size="small">
            <el-table-column prop="model_name" label="模型" min-width="170" show-overflow-tooltip>
              <template #default="{ row }"><span class="mono">{{ row.model_name }}</span></template>
            </el-table-column>
            <el-table-column v-for="metric in metrics" :key="metric" :label="METRIC_LABEL[metric]" align="center">
              <el-table-column label="训练" align="right" width="84">
                <template #default="{ row }">{{ formatPercent(row.metrics?.train?.[metric]) }}</template>
              </el-table-column>
              <el-table-column label="验证" align="right" width="84">
                <template #default="{ row }">{{ formatPercent(row.metrics?.valid?.[metric]) }}</template>
              </el-table-column>
            </el-table-column>
          </el-table>
          <div v-if="result.failed?.length" class="failed">
            <div v-for="item in result.failed" :key="item.algo" class="failed-item">
              <span class="pill danger">{{ item.algo }}</span>
              <span class="muted">{{ item.reason }}</span>
            </div>
          </div>
        </div>

        <div class="chart-panel">
          <div class="row wrap">
            <el-select v-model="chartMetric" size="small" style="width: 140px">
              <el-option v-for="metric in metrics" :key="metric" :label="METRIC_LABEL[metric]" :value="metric" />
            </el-select>
            <el-radio-group v-model="chartType" size="small">
              <el-radio-button value="bar">柱状图</el-radio-button>
              <el-radio-button value="radar">雷达图</el-radio-button>
            </el-radio-group>
          </div>
          <EChart :option="chartType === 'bar' ? barOption : radarOption" height="300px" />
        </div>
      </div>

      <div class="model-cards">
        <article v-for="item in successModels" :key="item.model_name" class="model-card">
          <div class="row-between">
            <strong class="mono">{{ item.model_name }}</strong>
            <el-checkbox
              :model-value="state.selectedModels.includes(item.model_name)"
              :disabled="state.savedModels.includes(item.model_name)"
              @change="toggleSave(item.model_name)"
            >
              保存
            </el-checkbox>
          </div>
          <div class="model-meta">
            <span class="pill primary">{{ LINE[result.line] || result.line }}</span>
            <span class="pill">{{ item.algo }}</span>
            <span class="pill">验证 F1 {{ formatPercent(item.metrics?.valid?.f1) }}</span>
            <span class="pill">{{ item.format }}</span>
          </div>
          <div class="row-between">
            <span class="soft">训练 / 验证已生成</span>
            <el-button size="small" @click="downloadModel(item.model_name)">下载模型文件</el-button>
          </div>
          <span v-if="state.savedModels.includes(item.model_name)" class="pill success">已保存</span>
        </article>
      </div>

      <div v-if="result.test_set" class="test-set">
        <div class="row-between wrap">
          <div>
            <strong>测试集</strong>
            <div class="muted">样本 {{ result.test_set.rows }} ｜ 正 {{ result.test_set.pos }} ｜ 负 {{ result.test_set.neg }}</div>
          </div>
          <div class="row wrap">
            <el-input v-model="state.testName" placeholder="测试集名称" style="width: 220px" :disabled="state.testSaved" />
            <el-button size="small" @click="exportTest('csv')">导出 CSV</el-button>
            <el-button size="small" @click="exportTest('excel')">导出 Excel</el-button>
            <el-checkbox v-model="state.saveTest" :disabled="state.testSaved">保存测试集</el-checkbox>
            <span v-if="state.testSaved" class="pill success">已保存</span>
          </div>
        </div>
      </div>

      <template #footer>
        <span class="muted">保存只复制当前产物；已保存的模型与测试集不会重复创建。</span>
        <el-button type="primary" :loading="saving" :disabled="!hasSelection" @click="saveAssets">保存选中资产</el-button>
      </template>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import SectionCard from '../components/SectionCard.vue'
import JobPanel from '../components/JobPanel.vue'
import DataSourcePicker from '../components/DataSourcePicker.vue'
import AlgorithmEditor from '../components/AlgorithmEditor.vue'
import EChart from '../components/EChart.vue'
import { listDatasets } from '../api/datasets'
import { listAlgorithms } from '../api/storage'
import * as trainApi from '../api/train'
import { getJob } from '../api/jobs'
import { humanError, LINE, METRIC_LABEL, formatPercent } from '../utils/format'
import { saveBlob } from '../utils/download'
import { useJob } from '../composables/useJob'
import { usePageState } from '../composables/usePageState'

const METRICS = ['accuracy', 'precision', 'recall', 'f1', 'auc', 'mcc']

function defaults() {
  return {
    step: 1,
    source: null,
    sourceInfo: null,
    algorithms: [],
    split: { mode: 'time', ratios: { train: 70, valid: 15, test: 15 } },
    job_id: null,
    result_ref: null,
    selectedModels: [],
    savedModels: [],
    saveTest: false,
    testName: '',
    testSaved: false
  }
}

const page = usePageState('train', defaults)
const state = page.state
const datasets = ref([])
const algorithms = ref([])
const algoError = ref('')
const pickerRef = ref(null)
const starting = ref(false)
const saving = ref(false)
const chartMetric = ref('f1')
const chartType = ref('bar')
const result = ref(null)

const { job, elapsed, progress, isRunning, isSuccess, isFailed, track, cancel, reset: resetJob } = useJob()

const metrics = computed(() => {
  const model = successModels.value[0]
  if (!model) return METRICS
  const keys = Object.keys(model.metrics?.valid || model.metrics?.train || {})
  return keys.length ? keys : METRICS
})

const running = computed(() => isRunning.value)
const lineLabel = computed(() => LINE[state.sourceInfo?.line] || '—')
const selectedCount = computed(() => state.algorithms.length)
const ratioTotal = computed(() => {
  const ratios = state.split.ratios
  return Number(ratios.train || 0) + Number(ratios.valid || 0) + Number(ratios.test || 0)
})
const splitPreview = computed(() => {
  const n = Number(state.sourceInfo?.sample_count || 0)
  const r = state.split.ratios
  return {
    train: Math.floor((n * Number(r.train || 0)) / 100),
    valid: Math.floor((n * Number(r.valid || 0)) / 100),
    test: Math.max(0, n - Math.floor((n * Number(r.train || 0)) / 100) - Math.floor((n * Number(r.valid || 0)) / 100))
  }
})
const canRun = computed(() =>
  state.source && state.sourceInfo && state.algorithms.length > 0 && ratioTotal.value === 100 && !running.value && !starting.value
)
const successModels = computed(() => (result.value?.models || []).filter((item) => item.status === 'success'))
const hasSelection = computed(() =>
  (state.saveTest && state.testName.trim() && !state.testSaved) ||
  state.selectedModels.some((name) => !state.savedModels.includes(name))
)
const algorithmStatus = computed(() => {
  if (!job.value) return []
  const done = job.value.done || 0
  return state.algorithms.map((item, index) => ({
    algo: item.algo,
    done: done > index,
    running: isRunning.value && done === index,
    stage: job.value.current_stage || ''
  }))
})

const barOption = computed(() => {
  const names = successModels.value.map((item) => item.algo)
  return {
    grid: { left: 40, right: 18, top: 40, bottom: 30 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['训练', '验证'], top: 6 },
    xAxis: { type: 'category', data: names, axisLine: { lineStyle: { color: '#cbd5e1' } } },
    yAxis: { type: 'value', min: 0, max: 1, splitLine: { lineStyle: { color: '#eef2f8' } } },
    series: [
      {
        name: '训练',
        type: 'bar',
        data: successModels.value.map((item) => item.metrics?.train?.[chartMetric.value] ?? null),
        itemStyle: { color: '#93c5fd', borderRadius: [5, 5, 0, 0] },
        barMaxWidth: 26
      },
      {
        name: '验证',
        type: 'bar',
        data: successModels.value.map((item) => item.metrics?.valid?.[chartMetric.value] ?? null),
        itemStyle: { color: '#0f766e', borderRadius: [5, 5, 0, 0] },
        barMaxWidth: 26
      }
    ]
  }
})

const radarOption = computed(() => {
  const indicators = ['precision', 'recall', 'f1', 'auc', 'mcc'].map((key) => ({ name: METRIC_LABEL[key], max: 1 }))
  return {
    tooltip: {},
    legend: { bottom: 0, type: 'scroll' },
    radar: {
      indicator: indicators,
      radius: '62%',
      splitLine: { lineStyle: { color: '#e2e8f0' } },
      axisName: { color: '#64748b', fontSize: 11 }
    },
    series: [{
      type: 'radar',
      data: successModels.value.map((item, index) => ({
        name: item.algo,
        value: ['precision', 'recall', 'f1', 'auc', 'mcc'].map((key) => item.metrics?.valid?.[key] ?? 0),
        areaStyle: { opacity: 0.08 },
        lineStyle: { width: 2, color: ['#0f766e', '#2563eb', '#d97706', '#7c3aed'][index % 4] }
      }))
    }]
  }
})

function clearResult() {
  result.value = null
  state.job_id = null
  state.result_ref = null
}

function onSource(value) {
  state.source = value
  if (!value) {
    state.sourceInfo = null
    clearResult()
    state.algorithms = []
    state.selectedModels = []
    state.savedModels = []
  }
}

async function onValidated(info) {
  state.sourceInfo = info
  clearResult()
  state.selectedModels = []
  state.savedModels = []
  state.testSaved = false
  state.saveTest = false
  if (!info) {
    state.algorithms = []
    algorithms.value = []
    state.testName = ''
    state.step = 1
    return
  }
  state.step = 2
  state.testName = `${info.label}-test`
  await loadAlgorithms(info.line)
}

async function loadAlgorithms(line) {
  algoError.value = ''
  try {
    const data = await listAlgorithms({ line })
    algorithms.value = data.items
    state.algorithms = []
  } catch (error) {
    algoError.value = humanError(error)
    algorithms.value = []
  }
}

async function loadDatasets() {
  try {
    const data = await listDatasets({ scope: 'mine', page_size: 100 })
    datasets.value = data.items.filter((item) => ['git_repo', 'upload', 'clean'].includes(item.source_type))
  } catch (error) {
    datasets.value = []
  }
}

function toggleSave(name) {
  if (state.selectedModels.includes(name)) {
    state.selectedModels = state.selectedModels.filter((item) => item !== name)
  } else {
    state.selectedModels = [...state.selectedModels, name]
  }
}

async function startTrain() {
  if (!canRun.value) return
  starting.value = true
  clearResult()
  state.selectedModels = []
  state.savedModels = []
  state.testSaved = false
  state.step = 4
  try {
    const data = await trainApi.run({
      source: state.source,
      algorithms: state.algorithms,
      split: state.split
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
    await ElMessageBox.confirm('确认取消训练？本轮结果将被丢弃，不可保存。', '取消训练', {
      type: 'warning',
      confirmButtonText: '取消训练',
      cancelButtonText: '继续等待'
    })
    await cancel()
    clearResult()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(humanError(error))
  }
}

async function loadResult(jobId) {
  const data = await trainApi.getResult(jobId)
  result.value = data
  state.job_id = jobId
  state.result_ref = { job_id: jobId, kind: 'train' }
  state.step = 5
  if (!state.testName) state.testName = data.test_set?.name || `test-${jobId.slice(4, 12)}`
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
    }
    if (value === 'failed' && job.value?.error_message) ElMessage.error(job.value.error_message)
    if (value === 'cancelled') {
      clearResult()
    }
  }
)

async function downloadModel(name) {
  if (!state.job_id) return
  try {
    const response = await trainApi.downloadOutput(state.job_id, name)
    saveBlob(response, `${name}.${name.includes('dnn') || name.includes('tabnet') ? 'pt' : 'pkl'}`)
  } catch (error) {
    ElMessage.error(humanError(error))
  }
}

async function exportTest(format) {
  if (!state.job_id) return
  try {
    const response = await trainApi.exportTestSet(state.job_id, {
      filename: state.testName.trim() || `test-${state.job_id.slice(4, 12)}`,
      format
    })
    saveBlob(response, `${state.testName.trim() || 'test'}.${format === 'excel' ? 'xlsx' : 'csv'}`)
  } catch (error) {
    ElMessage.error(humanError(error))
  }
}

async function saveAssets() {
  if (!state.job_id) return
  saving.value = true
  try {
    const data = await trainApi.saveAssets({
      job_id: state.job_id,
      model_names: state.selectedModels,
      save_test: state.saveTest,
      test_name: state.testName
    })
    state.savedModels = Array.from(new Set([...state.savedModels, ...(data.saved_models || [])]))
    if (data.test_dataset_id) state.testSaved = true
    ElMessage.success('资产已保存')
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    saving.value = false
  }
}

async function confirmReset() {
  try {
    await ElMessageBox.confirm('重置会清空本页进度与未保存模型，已保存资产不受影响。', '重置页面', {
      type: 'warning',
      confirmButtonText: '重置',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  resetJob()
  pickerRef.value?.reset()
  algorithms.value = []
  await page.reset()
}

async function restore() {
  if (state.sourceInfo?.line && !algorithms.value.length) await loadAlgorithms(state.sourceInfo.line)
  const jobId = state.result_ref?.job_id || state.job_id
  if (!jobId) return
  try {
    const data = await getJob(jobId)
    if (data.status === 'success') {
      job.value = data
      await loadResult(jobId)
    } else if (['queued', 'running'].includes(data.status)) {
      state.job_id = jobId
      track(jobId, data.total)
    } else {
      clearResult()
    }
  } catch (error) {
    clearResult()
  }
}

onMounted(async () => {
  await page.ready
  await loadDatasets()
  await restore()
})
</script>

<style scoped>
.split {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ratio-row {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}

.ratio-row label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--text-muted);
  font-weight: 600;
}

.ratio-row :deep(.el-input-number) {
  width: 80px;
}

.preview {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--surface-muted);
  border: 1px solid var(--border);
  font-size: 12.5px;
}

.preview strong {
  color: var(--text);
}

.form-error {
  color: var(--danger);
  font-size: 12.5px;
}

.job-table {
  margin-top: 12px;
}

.result-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.75fr);
  gap: 16px;
}

.table-wrap {
  overflow-x: auto;
}

.failed {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.failed-item {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12.5px;
}

.chart-panel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
  background: var(--surface-muted);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.model-cards {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 12px;
}

.model-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--surface);
}

.model-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.test-set {
  margin-top: 16px;
  padding: 14px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface-muted);
}

@media (max-width: 900px) {
  .result-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
