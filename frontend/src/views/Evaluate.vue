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
        :summary="selectedSource?.label || '尚未选择已预测数据'"
      >
        <div class="field">
          <span class="field-label">已预测数据</span>
          <el-select
            id="eval-source"
            v-model="draft.source_id"
            :placeholder="sources.length ? '请选择已预测数据' : '暂无已预测数据，请先完成模型预测'"
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
        <p
          v-if="sourcesLoading"
          class="status-line"
        >
          正在读取已预测数据…
        </p>
        <p
          v-if="sourcesError"
          class="validation"
        >
          {{ sourcesError }}
        </p>
        <InfoGrid
          v-if="selectedSource"
          :items="sourceInfo"
        />
      </StepSection>
      <StepSection
        v-for="(group, index) in choiceGroups"
        :key="group.title"
        :index="stepNo(index + 2)"
        :title="group.title"
        :state="stepState(1)"
        collapsible
        :summary="`${group.options.filter(item => draft.metrics.includes(item.key)).length} / ${group.options.length} 已选`"
      >
        <ChoiceGroup
          v-model="draft.metrics"
          name="eval-metric"
          multiple
          :options="group.options"
          :disabled="busy || auth"
        />
      </StepSection>
      <p
        v-if="!sourcesLoading && !metricGroups.length"
        class="status-line"
      >
        暂无可用的评估指标，请稍后重试。
      </p>
      <StepSection
        :index="thresholdStepIndex"
        title="输出设置"
        tag="阈值沿用预测结果"
        :state="stepState(2)"
        collapsible
        :summary="draft.output_format === 'xlsx' ? 'Excel 指标表' : 'CSV 指标表'"
      >
        <div class="field">
          <span class="field-label">评估图集 zip 名称</span>
          <el-input
            id="eval-zip-name"
            v-model="draft.figure_zip_name"
            :disabled="busy || auth"
            placeholder="留空按批次自动命名"
          />
        </div>
        <div class="field">
          <span class="field-label">评估指标表名称</span>
          <el-input
            id="eval-metrics-name"
            v-model="draft.metrics_name"
            :disabled="busy || auth"
            placeholder="留空按批次自动命名"
          />
        </div>
        <div class="field">
          <span class="field-label">指标表格式</span>
          <el-radio-group
            v-model="draft.output_format"
            :disabled="busy || auth"
          >
            <el-radio value="csv">
              CSV
            </el-radio>
            <el-radio value="xlsx">
              Excel
            </el-radio>
          </el-radio-group>
        </div>
        <p class="status-line">
          判定阈值、预测标签沿用已保存的预测结果，评估阶段不重新判定。
        </p>
      </StepSection>
      <StepSection
        :index="confirmStepIndex"
        title="确认配置"
        :state="stepState(3)"
        collapsible
        :summary="`${selectedSource?.label || '未选择数据'} · ${draft.metrics.length} 个指标`"
      >
        <InfoGrid :items="confirmInfo" />
      </StepSection>
      <StepSection
        :index="runStepIndex"
        title="运行"
        :state="stepState(4)"
        sticky
      >
        <el-button
          data-testid="eval-run"
          class="run-button"
          type="primary"
          size="large"
          :loading="busy"
          :disabled="busy || auth || isRunning || !hasInput || !draft.metrics.length"
          @click="submit"
        >
          开始评估
        </el-button>
      </StepSection>
    </template>
    <template #after>
      <JobProgress
        title="评估进度"
        test-id="eval-job"
        :job="evaluating.job"
        :text="progressText"
        retry-test-id="eval-retry"
        cancel-test-id="eval-cancel"
        :retry-disabled="auth"
        :cancel-disabled="auth"
        @retry="retry"
        @cancel="cancel"
      />
      <JobResultPanel
        title="评估结果"
        test-id="eval-result"
        :stats="resultStats"
        :error="outputError"
        :summary-rows="resultSummaryRows"
      >
        <el-collapse v-model="openSections">
          <el-collapse-item
            title="性能指标图"
            name="charts"
          >
            <div
              v-if="images.length"
              class="charts"
            >
              <figure
                v-for="img in images"
                :key="img.name"
              >
                <img
                  :src="img.url"
                  :alt="img.name"
                ><figcaption>{{ img.name }}</figcaption>
              </figure>
            </div>
            <p
              v-else
              class="status-line"
            >
              评估完成后在这里展示该模型的 ROC、PR、混淆矩阵、校准与工作量曲线等指标图。
            </p>
          </el-collapse-item>
        </el-collapse>
      </JobResultPanel>
      <section
        class="panel"
        data-pane="wide"
        aria-label="结果文件"
        data-testid="eval-files"
      >
        <div class="section-heading">
          <h2>结果文件</h2>
        </div>
        <OutputFiles
          v-if="evalFiles.length"
          :items="evalFiles"
          @download="item => download(item.name)"
        />
        <p
          v-else
          class="status-line"
        >
          评估成功后在这里下载指标表与性能指标图集。
        </p>
      </section>
    </template>
  </ToolWorkspace>
</template>

<script setup>
import { computed, onActivated, onDeactivated, reactive, ref } from 'vue'
import ChoiceGroup from '../components/ChoiceGroup.vue'
import InfoGrid from '../components/InfoGrid.vue'
import JobProgress from '../components/JobProgress.vue'
import JobResultPanel from '../components/JobResultPanel.vue'
import OutputFiles from '../components/OutputFiles.vue'
import StepRail from '../components/StepRail.vue'
import StepSection from '../components/StepSection.vue'
import ToolWorkspace from '../components/ToolWorkspace.vue'
import { cancelJob, fetchEvaluateOutput, getEvaluateMetrics, getJob, getJobs, retryJob, runEvaluate } from '../api'
import { artifactSources, loadArtifactJobs } from '../utils/artifacts'
import { evaluating } from '../utils/evaluate'
import { formatTime } from '../utils/datetime'
import { scrollToResults } from '../utils/scroll'

defineOptions({ name: 'EvaluateTool' })
const hasInput = computed(() => Boolean(draft.source_id))
const registry = ref([]), sourceJobs = reactive({ items: [], total: 0, page: 1 })
const sources = computed(() => artifactSources(sourceJobs.items, ['.csv', '.xlsx']))
const selectedSource = computed(() => sources.value.find(item => item.value === draft.source_id))
const selectedJob = computed(() => sourceJobs.items.find(job => job.job_id === selectedSource.value?.job_id))
const sourcesLoading = ref(false), sourcesError = ref('')
const busy = ref(false), auth = ref(false), error = ref(''), refreshing = ref(false), downloading = ref(false)
const draft = reactive({
  metrics: [],
  source_id: '',
  figure_zip_name: '',
  metrics_name: '',
  output_format: 'csv'
})
const images = ref([]), outputError = ref('')
const openSections = ref(['charts'])
let timer, mounted = true, outputJob = '', epoch = 0
let activated = false
const result = computed(() => evaluating.job?.output_ref_json || {})
const summary = computed(() => result.value.summary || {})
const resultStats = computed(() => [
  { label: '评估模型', value: (summary.value.models || []).length || '—' },
  { label: '样本行数', value: summary.value.rows ?? '—' },
  { label: '已选指标', value: draft.metrics.length || '—' },
  { label: '不可用指标', value: (summary.value.unavailable || []).length }
])
const resultSummaryRows = computed(() => evaluating.job?.status !== 'success' ? [] : [
  { label: '评估数据', value: selectedJob.value?.label || '—' },
  { label: '样本行数', value: summary.value.rows ?? '—' },
  { label: '判定阈值', value: thresholdText.value },
  { label: '已选指标', value: `${draft.metrics.length} 个` },
  { label: '不可用指标', value: (summary.value.unavailable || []).length },
  { label: '完成时间', value: formatTime(evaluating.job?.finished_at || evaluating.job?.created_at) }
])
const metricGroups = computed(() => [
  { title: '排序质量', options: registry.value.filter(item => !item.threshold_dependent && !item.effort_aware) },
  { title: '分类质量', options: registry.value.filter(item => item.threshold_dependent && !item.effort_aware) },
  { title: '工作量感知', options: registry.value.filter(item => item.effort_aware) }
].filter(group => group.options.length))
const stepNo = index => String(index).padStart(2, '0')
const thresholdText = computed(() => summary.value.decision_threshold != null
  ? Number(summary.value.decision_threshold).toFixed(2)
  : '沿用预测结果')
const thresholdStepIndex = computed(() => stepNo(metricGroups.value.length + 2))
const confirmStepIndex = computed(() => stepNo(metricGroups.value.length + 3))
const runStepIndex = computed(() => stepNo(metricGroups.value.length + 4))
// 顶部步骤轨道：忽略动态指标分组，只体现「选数据 → 选指标 → 输出 → 确认 → 运行」主干。
const railSteps = [
  { title: '选择输入', note: '已预测数据' },
  { title: '评估指标', note: '指标组合' },
  { title: '输出设置', note: 'effort-aware' },
  { title: '确认配置', note: '运行前核对' },
  { title: '运行', note: '开始评估' }
]
const activeStep = computed(() => {
  if (isRunning.value) return 4
  if (evaluating.job?.status === 'success') return 4
  if (!hasInput.value) return 0
  if (!draft.metrics.length) return 1
  return 3
})
function stepState(index) {
  if (evaluating.job?.status === 'success') return 'done'
  if (index < activeStep.value) return 'done'
  return index === activeStep.value ? 'current' : 'upcoming'
}
const evalFiles = computed(() => (result.value.outputs || [])
  .filter(item => item.name?.endsWith('.zip') || (
    /\.(csv|xlsx)$/.test(item.name || '')
    && !/^evaluate_(metrics|confusion)_/.test(item.name)
  ))
  .map(item => ({
    ...item,
    label: item.name.endsWith('.zip') ? '性能指标图集' : '评估指标表',
    testid: `eval-download-${item.name}`,
    disabled: auth.value || downloading.value
  })))
const isRunning = computed(() => ['queued', 'running'].includes(evaluating.job?.status))
const progressText = computed(() => {
  const status = evaluating.job?.status
  if (!status) return '当前未开始，选择预测结果后开始评估'
  if (status === 'queued') return '当前正在排队等待执行'
  if (status === 'running') return `当前正在评估，已完成 ${evaluating.job.done || 0} / ${evaluating.job.total || 0} 项`
  if (status === 'success') return '当前评估已完成'
  if (status === 'failed') return '当前评估失败，可重试原任务'
  if (status === 'cancelled') return '当前评估已取消'
  return ''
})
const metricLabels = {
  auc: 'AUC', ap: 'AP', f1: 'F1', precision: '精确率', recall: '召回率', accuracy: '准确率',
  'ap_effort': '工作量 AP', 'f1_effort': '工作量 F1', 'recall_effort': '工作量召回率'
}
const metricLabel = key => metricLabels[key] || (registry.value.find(item => item.key === key)?.name || key)
const selectedMetricText = computed(() => draft.metrics.length
  ? `${draft.metrics.length} 项，${draft.metrics.map(metricLabel).join('，')}`
  : '未选择')
const sourceInfo = computed(() => [
  { label: '预测任务', value: selectedJob.value?.label || '未提供' },
  { label: '预测结果', value: selectedJob.value?.summary || '未提供' },
  { label: '数据文件', value: selectedSource.value.name, mono: true },
  { label: '清单文件', value: selectedSource.value.companions?.[0] || '随数据一起提交', mono: true },
  { label: '生成时间', value: formatTime(selectedJob.value?.created_at) },
  { label: '任务状态', value: selectedJob.value?.statusLabel || '成功' }
])
const confirmInfo = computed(() => [
  { label: '输入数据', value: selectedJob.value?.label || '未选择' },
  { label: '样本规模', value: selectedJob.value?.summary || '未提供' },
  { label: '已选指标', value: selectedMetricText.value, span: true },
  { label: '判定阈值', value: '沿用预测结果' },
  { label: '输出', value: '评估图集 zip 与评估指标表' }
])
const choiceGroups = computed(() => metricGroups.value.map(group => ({
  title: group.title,
  options: group.options.map(item => ({
    key: item.key,
    label: metricLabel(item.key),
    tip: item.description
  }))
})))
function message(err) {
  if (err.code === 40100) { auth.value = true; return '登录已失效，请重新登录' }
  return err.code === 50000 ? '评估服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
async function loadSources(page = 1) {
  sourcesLoading.value = true; sourcesError.value = ''
  try {
    const [data, jobs] = await Promise.all([
      getEvaluateMetrics(),
      loadArtifactJobs('predict_batch', { page, size: 20 })
    ])
    registry.value = Array.isArray(data.metrics) ? data.metrics : []
    draft.metrics = [...(data.defaults.metrics_selected || ['auc', 'ap', 'f1', 'precision', 'recall', 'accuracy'])]
    Object.assign(sourceJobs, jobs)
    // 默认选中最新一批已预测数据，指标已由后端给出默认组合，用户可直接开始评估。
    if (!jobs.items.some(job => job.files.some(file => file.value === draft.source_id))) {
      const preferred = sources.value.find(file => /predictions/i.test(file.name)) || sources.value[0]
      draft.source_id = preferred?.value || ''
    }
  } catch (err) { sourcesError.value = message(err) }
  finally { sourcesLoading.value = false }
}
function resetOutputs() { epoch++; outputJob = ''; outputError.value = ''; for (const img of images.value) URL.revokeObjectURL(img.url); images.value = [] }
async function submit() {
  if (busy.value || auth.value || isRunning.value || !hasInput.value || !draft.metrics.length) return
  busy.value = true; error.value = ''
  try {
    const config = {
      prediction_job_id: selectedSource.value?.job_id,
      metrics: [...draft.metrics],
      primary_metric: draft.metrics[0],
      effort_enabled: false,
      output_format: draft.output_format
    }
    if (draft.figure_zip_name.trim()) config.figure_zip_name = draft.figure_zip_name.trim()
    if (draft.metrics_name.trim()) config.metrics_name = draft.metrics_name.trim()
    const accepted = await runEvaluate(config)
    if (!accepted?.job_id) throw new Error('评估任务响应不完整')
    resetOutputs(); evaluating.request = config; evaluating.job = accepted
    scrollToResults()
    await refreshJob()
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
async function loadOutputs(id) {
  if (outputJob === id) return
  const ownEpoch = epoch, reference = result.value
  try {
    const staged = []
    for (const item of (reference.outputs || []).filter(i => i.name.endsWith('.png'))) {
      const blob = await fetchEvaluateOutput(id, item.name)
      if (!mounted || ownEpoch !== epoch) return
      staged.push({ name: item.name, blob })
    }
    if (!mounted || ownEpoch !== epoch || evaluating.job?.job_id !== id) return
    for (const img of images.value) URL.revokeObjectURL(img.url)
    images.value = staged.map(i => ({ name: i.name, url: URL.createObjectURL(i.blob) }))
    outputJob = id; outputError.value = ''
  } catch (err) { if (mounted && ownEpoch === epoch) outputError.value = message(err) }
}
async function refreshJob() {
  if (!evaluating.job?.job_id || refreshing.value || auth.value) return
  clearTimeout(timer); refreshing.value = true
  const id = evaluating.job.job_id
  try {
    const data = await getJob(id)
    if (!mounted || evaluating.job?.job_id !== id) return
    evaluating.job = data
    if (data.status === 'success') await loadOutputs(id)
  } catch (err) { if (mounted && evaluating.job?.job_id === id) error.value = message(err) }
  finally {
    refreshing.value = false
    if (mounted) {
      if (evaluating.job?.job_id !== id) refreshJob()
      else if (['queued', 'running'].includes(evaluating.job?.status)) timer = setTimeout(refreshJob, 1500)
    }
  }
}
async function retry() { try { const data = await retryJob(evaluating.job.job_id); resetOutputs(); evaluating.job = { ...evaluating.job, ...data }; await refreshJob() } catch (err) { error.value = message(err) } }
async function cancel() { try { const data = await cancelJob(evaluating.job.job_id); evaluating.job = { ...evaluating.job, ...data }; clearTimeout(timer) } catch (err) { error.value = message(err) } }
async function download(name) {
  downloading.value = true
  try { const blob = await fetchEvaluateOutput(evaluating.job.job_id, name), url = URL.createObjectURL(blob); try { const link = document.createElement('a'); link.href = url; link.download = name; link.click() } finally { URL.revokeObjectURL(url) } }
  catch (err) { error.value = message(err) }
  finally { downloading.value = false }
}
onActivated(async () => {
  mounted = true
  // 二次进入保留模型、指标与 effort 选择，只续接评估进度。
  if (activated) { await refreshJob(); return }
  activated = true
  await loadSources()
  if (!evaluating.job) { try { const data = await getJobs({ kind: 'evaluate', size: 1 }); evaluating.job = data.items?.[0] || null } catch (err) { error.value = message(err) } }
  await refreshJob()
})
onDeactivated(() => { mounted = false; clearTimeout(timer) })
</script>

<style scoped>
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr)); gap: 18px; margin-top: 16px; }
figure { margin: 0; min-width: 0; padding: 12px; border: 1px solid var(--ui-border); border-radius: var(--ui-radius-lg); background: var(--ui-surface-subtle); }
img { display: block; width: 100%; height: auto; border-radius: var(--ui-radius-sm); }
figcaption { margin-top: 8px; color: var(--ui-text-muted); font-size: var(--ui-font-hint); overflow-wrap: anywhere; }
</style>

<style>
.eval-metric-tip.el-popper {
  max-width: 320px;
  padding: 10px 12px;
  font-size: var(--ui-font-md);
  line-height: 1.6;
}
</style>
