<template>
  <ToolWorkspace
    hide-tabs
    model-value="config"
  >
    <template #config>
      <el-alert
        v-if="error"
        :title="error"
        type="error"
        :closable="false"
        show-icon
      />
      <StepRail
        :steps="railSteps"
        :active="activeStep"
      />
      <StepSection
        index="01"
        title="选择输入"
        :state="stepState(0)"
        collapsible
        :summary="inputSummary"
      >
        <div class="fields">
          <div class="field">
            <span class="field-label">已训练模型</span>
            <el-select
              id="predict-source"
              v-model="draft.source_id"
              placeholder="请选择已训练模型"
              :disabled="busy || auth || sourcesLoading"
              filterable
            >
              <el-option
                v-for="item in sources"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div>
          <div class="field">
            <span class="field-label">待预测测试集</span>
            <el-select
              id="predict-testset"
              v-model="draft.test_id"
              :placeholder="testSources.length ? '请选择测试集' : '暂无测试集，请先完成模型训练'"
              :disabled="busy || auth || sourcesLoading || !testSources.length"
              filterable
            >
              <el-option
                v-for="item in testSources"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </div>
        </div>
        <p
          v-if="sourcesLoading"
          class="status-line"
        >
          正在读取已训练模型与测试集…
        </p>
        <p
          v-if="sourcesError"
          class="validation"
        >
          {{ sourcesError }}
        </p>
        <InfoGrid
          v-if="selectedSource || selectedTest"
          :items="sourceInfo"
        />
      </StepSection>
      <StepSection
        index="02"
        title="判定阈值"
        :state="stepState(1)"
        collapsible
        :summary="`阈值 ${thresholdText}`"
      >
        <template #extra>
          <el-tag>{{ thresholdText }}</el-tag>
        </template>
        <div class="field">
          <el-slider
            v-model="draft.threshold"
            :min="0.05"
            :max="0.95"
            :step="0.01"
            :disabled="busy || auth"
            aria-label="判定阈值"
          />
        </div>
      </StepSection>
      <StepSection
        index="03"
        title="确认配置"
        :state="stepState(2)"
        collapsible
        :summary="`${selectedSource?.label || '未选择模型'} · 阈值 ${thresholdText}`"
      >
        <InfoGrid :items="confirmInfo" />
      </StepSection>
      <StepSection
        index="04"
        title="运行"
        :state="stepState(3)"
        sticky
      >
        <el-button
          data-testid="predict-run"
          class="run-button"
          type="primary"
          size="large"
          :loading="busy"
          :disabled="busy || auth || isRunning || !canRun"
          @click="submit"
        >
          开始预测
        </el-button>
      </StepSection>
    </template>
    <template #after>
      <JobProgress
        title="预测进度"
        test-id="predict-job"
        :job="predicting.job"
        :text="progressText"
        retry-test-id="predict-retry"
        cancel-test-id="predict-cancel"
        :retry-disabled="auth || refreshing"
        :cancel-disabled="auth"
        @retry="retry"
        @cancel="cancel"
      />
      <JobResultPanel
        title="预测结果"
        test-id="predict-result"
        :stats="resultStats"
        :error="outputError"
        :summary-rows="resultSummaryRows"
      >
        <el-collapse v-model="openSections">
          <el-collapse-item
            title="预测预览"
            name="preview"
          >
            <DataTable
              v-if="preview"
              test-id="predict-preview"
              :columns="previewColumns"
              :rows="previewRows"
              row-key="commit_hash"
              clickable
              empty="暂无预览数据"
              @row-click="openDetail"
            >
              <template #[`cell.actions`]="{ row }">
                <el-button
                  link
                  type="primary"
                  @click.stop="openDetail(row)"
                >
                  查看详情
                </el-button>
              </template>
            </DataTable>
            <el-pagination
              v-if="preview?.total"
              class="pagination"
              background
              layout="total, prev, pager, next"
              :current-page="previewPage"
              :page-size="previewSize"
              :total="preview.total"
              hide-on-single-page
              @current-change="loadPreview"
            />
            <p
              v-else
              class="status-line"
            >
              预测完成后在这里展示全部结果，可翻页查看。
            </p>
          </el-collapse-item>
        </el-collapse>
      </JobResultPanel>
      <section
        class="panel"
        data-pane="wide"
        aria-label="结果文件"
        data-testid="predict-files"
      >
        <div class="section-heading">
          <h2>结果文件</h2>
        </div>
        <OutputFiles
          :items="downloadItems"
          @download="item => download(item.name)"
        />
      </section>
    </template>
  </ToolWorkspace>
</template>

<script setup>
import { computed, onActivated, onDeactivated, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import DataTable from '../components/DataTable.vue'
import JobProgress from '../components/JobProgress.vue'
import JobResultPanel from '../components/JobResultPanel.vue'
import OutputFiles from '../components/OutputFiles.vue'
import InfoGrid from '../components/InfoGrid.vue'
import StepRail from '../components/StepRail.vue'
import StepSection from '../components/StepSection.vue'
import ToolWorkspace from '../components/ToolWorkspace.vue'
import { cancelJob, fetchPredictOutput, getJob, getJobs, getModelsStatus, getPredictPreview, retryJob, runPredict } from '../api'
import { artifactSources, loadArtifactJobs, materializeArtifact } from '../utils/artifacts'
import { predicting } from '../utils/predict'
import { saveBlob } from '../utils/download'
import { scrollToResults } from '../utils/scroll'
import { configuration } from '../utils/thresholds'

defineOptions({ name: 'PredictTool' })
const router = useRouter()
const sourceJobs = reactive({ items: [], total: 0, page: 1 })
// 模型下拉直接来自已登记工件（model_artifact），逐个 .pkl 展示模型名，不再要求选择 ZIP。
const registry = reactive({ items: [] })
const sources = computed(() => registry.items
  .filter(item => item.artifact_status === 'available')
  .map(item => ({ value: item.model_name, label: item.model_name, model: item })))
const testSources = computed(() => artifactSources(sourceJobs.items, ['.csv', '.xlsx'])
  .filter(item => item.name.includes('train_testset')))
const selectedSource = computed(() => sources.value.find(item => item.value === draft.source_id))
const selectedJob = computed(() => sourceJobs.items.find(job => (job.models || []).some(
  model => model.model_name === draft.source_id && model.status === 'success')))
const selectedTest = computed(() => testSources.value.find(item => item.value === draft.test_id))
const lineLabel = computed(() => selectedSource.value?.model?.line === 'semantic' ? '语义' : '专家特征')
const artifactStatus = computed(() => {
  const status = selectedSource.value?.model?.artifact_status
  return status === 'available' ? '可用' : status === 'retired' ? '已退役' : (status || '未提供')
})
const selectedTestJob = computed(() => sourceJobs.items.find(job => job.job_id === selectedTest.value?.job_id))
const sampleScale = computed(() => {
  const metrics = selectedTestJob.value?.metrics || []
  const value = label => metrics.find(item => item.label === label)?.value
  const train = value('训练行数'), test = value('测试行数')
  return train != null && test != null ? `${train} → ${test} 条` : '未提供'
})
const sourceInfo = computed(() => [
  { label: '模型名称', value: selectedSource.value?.label || '未选择', mono: true },
  { label: '算法', value: selectedSource.value?.model?.algo || '未提供' },
  { label: '特征线', value: lineLabel.value },
  { label: '模型版本', value: selectedSource.value?.model?.version_key || '未提供', mono: true },
  { label: '训练任务', value: selectedJob.value?.label || '未提供' },
  { label: '状态', value: artifactStatus.value },
  { label: '测试集', value: selectedTest.value?.name || '未选择', mono: true },
  { label: '样本规模', value: sampleScale.value },
  { label: '数据清单', value: selectedTest.value?.companions?.[0] || '随测试集一起提交', mono: true },
  { label: '生成时间', value: formatTime(selectedSource.value?.model?.trained_at || selectedJob.value?.created_at) }
])
const confirmInfo = computed(() => [
  { label: '输入模型', value: selectedSource.value?.label || '未选择', mono: true },
  { label: '模型任务', value: selectedJob.value?.label || '未提供' },
  { label: '待测数据', value: selectedTest.value?.name || '未选择', mono: true },
  { label: '样本规模', value: sampleScale.value },
  { label: '判定阈值', value: thresholdText.value },
  { label: '数据清单', value: selectedTest.value?.companions?.[0] || '随测试集一起提交', mono: true },
  { label: '输出', value: '预测结果表（CSV），可在预览中翻页查看全部结果', span: true }
])
const sourcesLoading = ref(false), sourcesError = ref('')
// 判定阈值默认取系统设置里的当前值，允许本次运行单独调整；不填任何本地常量冒充配置。
function configuredThreshold() {
  const value = configuration.items.find(item => item.config_key === 'decision_threshold')?.value
  return typeof value === 'number' && value > 0 && value < 1 ? value : 0.5
}
const draft = reactive({ source_id: '', test_id: '', threshold: configuredThreshold() })
// 切换模型时默认带上同一次训练产出的测试集，仍可单独改选其它训练批次。
watch(() => draft.source_id, value => {
  const job = sourceJobs.items.find(item => (item.models || []).some(
    model => model.model_name === value && model.status === 'success'))
  const matched = testSources.value.find(item => item.job_id === job?.job_id)
  draft.test_id = matched?.value || testSources.value[0]?.value || ''
})
const thresholdText = computed(() => Number(draft.threshold || 0).toFixed(2))
// 折叠后的单行摘要：只保留模型与测试集名称，便于确认当前选择。
const inputSummary = computed(() => {
  const parts = [selectedSource.value?.label, selectedTest.value?.name].filter(Boolean)
  return parts.length ? parts.join(' · ') : '尚未选择模型与测试集'
})
const thresholdValid = computed(() => Number(draft.threshold) > 0 && Number(draft.threshold) < 1)
const busy = ref(false), auth = ref(false), error = ref(''), refreshing = ref(false), downloading = ref(false)
const preview = ref(null), outputError = ref('')
const previewPage = ref(1)
const previewSize = 12
const openSections = ref(['preview'])
let timer, mounted = true, jobEpoch = 0, outputJob = '', epoch = 0
let activated = false
const result = computed(() => predicting.job?.output_ref_json || {})
const summary = computed(() => result.value.summary || {})
const resultStats = computed(() => [
  { label: '输入提交', value: summary.value.input_rows ?? '—' },
  { label: '成功预测', value: summary.value.success_count ?? '—' },
  { label: '失败', value: summary.value.failed_count ?? '—' },
  { label: '判定阈值', value: summary.value.decision_threshold ?? Number(predicting.request?.decision_threshold ?? draft.threshold).toFixed(2) }
])
const previewColumns = computed(() => [
  ...(preview.value?.columns || []).map(key => ({ key, label: key, mono: key === 'commit_hash' })),
  { key: 'actions', label: '详情', width: '90px' }
])
const previewRows = computed(() => (preview.value?.preview || []).map(row => ({
  ...row,
  is_bug_inducing: row.is_bug_inducing == null || row.is_bug_inducing === '' ? '未标注' : row.is_bug_inducing
})))
// 预测只交付一张结果表。
const predictFiles = computed(() => (result.value.outputs || [])
  .filter(item => item.name.endsWith('.csv'))
  .map(item => ({
    ...item,
    label: '预测结果',
    testid: `predict-download-${item.name}`,
    disabled: auth.value || downloading.value
  })))
const downloadItems = computed(() => predictFiles.value)
const resultSummaryRows = computed(() => predicting.job?.status !== 'success' ? [] : [
  { label: '预测模型', value: summary.value.model_name || predicting.request?.model_name || '—', mono: true },
  { label: '待测数据', value: predicting.request?.test_name || '—', mono: true },
  { label: '判定阈值', value: thresholdText.value },
  { label: '失败样本', value: summary.value.failed_count ?? '—' },
  { label: '完成时间', value: formatTime(predicting.job?.finished_at || predicting.job?.created_at) },
  { label: '输出文件', value: `${predictFiles.value.length} 个` }
])
const isRunning = computed(() => ['queued', 'running'].includes(predicting.job?.status))
const progressText = computed(() => {
  const status = predicting.job?.status
  if (!status) return '当前未开始，选择模型与测试集后开始预测'
  if (status === 'queued') return '当前正在排队等待执行'
  if (status === 'running') return `当前正在预测，已完成 ${predicting.job.done || 0} / ${predicting.job.total || 0} 条提交`
  if (status === 'success') return '当前预测已完成，可查看结果并下载'
  if (status === 'failed') return '当前预测失败，可重试原任务'
  if (status === 'cancelled') return '当前预测已取消'
  return ''
})
const canRun = computed(() => Boolean(draft.source_id) && Boolean(draft.test_id) && thresholdValid.value)
// 顶部步骤轨道：输入齐备后自动推进，运行中与完成后收口到最后一步。
const railSteps = [
  { title: '选择输入', note: '模型与测试集' },
  { title: '判定阈值', note: '风险分界' },
  { title: '确认配置', note: '运行前核对' },
  { title: '运行', note: '开始预测' }
]
const activeStep = computed(() => {
  if (isRunning.value) return 3
  if (predicting.job?.status === 'success') return 3
  if (!canRun.value) return 0
  return 2
})
function stepState(index) {
  if (predicting.job?.status === 'success') return 'done'
  if (index < activeStep.value) return 'done'
  return index === activeStep.value ? 'current' : 'upcoming'
}
function formatTime(value) {
  if (!value) return '未提供'
  return String(value).replace('T', ' ').replace(/\.\d+Z?$/, '').replace('Z', '').slice(0, 16)
}
function message(err) {
  if (err.code === 40100) { auth.value = true; return '登录已失效，请重新登录' }
  return err.code === 50000 ? '预测服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
async function loadSources(page = 1) {
  sourcesLoading.value = true; sourcesError.value = ''
  try {
    const [jobs, models] = await Promise.all([
      loadArtifactJobs('train', { page, size: 20 }),
      getModelsStatus()
    ])
    Object.assign(sourceJobs, jobs)
    registry.items = models.items || []
    // 首次进入自动选中最新可用模型，并带出同批次测试集，减少一次手动选择。
    if (!sources.value.some(file => file.value === draft.source_id)) {
      draft.source_id = sources.value[0]?.value || ''
    }
    if (!testSources.value.some(file => file.value === draft.test_id)) {
      const jobId = sourceJobs.items.find(job => (job.models || []).some(
        model => model.model_name === draft.source_id && model.status === 'success'))?.job_id
      // 优先带出同批训练产出的测试集，没有匹配时退回最近的可用测试集。
      draft.test_id = testSources.value.find(file => file.job_id === jobId)?.value
        || testSources.value[0]?.value || ''
    }
  } catch (err) { sourcesError.value = message(err) }
  finally { sourcesLoading.value = false }
}
function resetOutputs() { epoch++; outputJob = ''; preview.value = null; previewPage.value = 1; outputError.value = '' }
async function submit() {
  if (busy.value || auth.value || isRunning.value || !canRun.value) return
  busy.value = true; error.value = ''
  try {
    // 模型通过 model_name 引用已登记 .pkl；只上传待预测测试集及其 manifest。
    const config = { model_name: draft.source_id, decision_threshold: Number(draft.threshold), force_recompute: false }
    const testFiles = await materializeArtifact(sourceJobs.items, draft.test_id, { extensions: ['.csv', '.xlsx'], includeCompanions: true })
    const accepted = await runPredict(config, testFiles)
    if (!accepted?.job_id || !['queued', 'running', 'success', 'failed'].includes(accepted.status)) throw new Error('预测任务响应不完整')
    resetOutputs()
    predicting.request = { ...config, model_name: selectedSource.value?.label || '', test_name: selectedTest.value?.name || '' }
    predicting.job = accepted
    scrollToResults()
    await refreshJob()
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
async function loadOutputs(id) {
  if (outputJob === id) return
  const ownEpoch = epoch
  try {
    const data = await getPredictPreview(id, { page: 1, size: previewSize })
    if (!mounted || ownEpoch !== epoch || predicting.job?.job_id !== id) return
    preview.value = data
    previewPage.value = data.page || 1
    outputJob = id; outputError.value = ''
  } catch (err) { if (mounted && ownEpoch === epoch) outputError.value = message(err) }
}
// 预测结果按页读取全部行。
async function loadPreview(page = 1) {
  const id = predicting.job?.job_id
  if (!id) return
  try {
    const data = await getPredictPreview(id, { page, size: previewSize })
    if (predicting.job?.job_id !== id) return
    preview.value = data
    previewPage.value = data.page || page
  } catch (err) { if (mounted) outputError.value = message(err) }
}
async function refreshJob() {
  if (!predicting.job?.job_id || refreshing.value || auth.value) return
  clearTimeout(timer); refreshing.value = true
  const id = predicting.job.job_id, token = ++jobEpoch
  try {
    const data = await getJob(id)
    if (!mounted || token !== jobEpoch || predicting.job?.job_id !== id) return
    if (data.kind !== 'predict_batch' || !['queued', 'running', 'success', 'failed', 'cancelled'].includes(data.status)) throw new Error('任务响应不完整')
    predicting.job = data
    if (data.status === 'success') await loadOutputs(id)
  } catch (err) { if (mounted && token === jobEpoch && predicting.job?.job_id === id) error.value = message(err) }
  finally {
    refreshing.value = false
    if (mounted && token === jobEpoch && ['queued', 'running'].includes(predicting.job?.status)) timer = setTimeout(refreshJob, 1500)
  }
}
async function retry() {
  try {
    const id = predicting.job.job_id
    await retryJob(id)
    resetOutputs(); predicting.job = await getJob(id)
    await refreshJob()
  } catch (err) { error.value = message(err) }
}
async function cancel() {
  try {
    const id = predicting.job.job_id
    await cancelJob(id)
    jobEpoch++; clearTimeout(timer)
    predicting.job = await getJob(id)
  } catch (err) { error.value = message(err) }
}
async function download(name) {
  downloading.value = true
  try { saveBlob(await fetchPredictOutput(predicting.job.job_id, name), name) }
  catch (err) { error.value = message(err) }
  finally { downloading.value = false }
}
// 每条预测结果都能进入详情：带上批次任务与模型，详情页据此显示该提交的预测结果。
function openDetail(row) {
  const hash = typeof row?.commit_hash === 'string' ? row.commit_hash.trim() : ''
  if (!hash) return
  const model = row.model_name || summary.value.model_name || predicting.request?.model_name || ''
  router.push({
    path: `/predict/commit/${hash}`,
    query: {
      ...(model ? { model_name: model } : {}),
      ...(predicting.job?.job_id ? { job_id: predicting.job.job_id } : {})
    }
  })
}
onActivated(async () => {
  mounted = true; jobEpoch++
  // 二次进入保留模型、数据集与阈值选择，只续接预测进度。
  if (activated) { await refreshJob(); return }
  activated = true
  await loadSources()
  if (!predicting.job) {
    try { const data = await getJobs({ kind: 'predict_batch', size: 1 }); predicting.job = data.items?.[0] || null }
    catch (err) { error.value = message(err) }
  }
  if (predicting.request) {
    // 回到页面时沿用上次运行选择的参数，避免阈值悄悄回到默认值。
    const threshold = Number(predicting.request.decision_threshold)
    if (threshold > 0 && threshold < 1) draft.threshold = threshold
  }
  await refreshJob()
})
onDeactivated(() => { mounted = false; clearTimeout(timer) })
</script>

<style scoped>
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>
