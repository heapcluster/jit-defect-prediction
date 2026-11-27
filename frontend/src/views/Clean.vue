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
        :summary="selectedDataset?.name || '尚未选择数据集'"
      >
        <div class="field">
          <span class="field-label">数据收集的数据集</span>
          <el-select
            id="clean-dataset"
            v-model="draft.dataset_id"
            :placeholder="datasets.length ? '请选择数据集' : '暂无数据集，请先在“数据收集”中保存'"
            :disabled="busy || auth"
            filterable
          >
            <el-option
              v-for="item in datasets"
              :key="item.dataset_id"
              :label="item.name"
              :value="item.dataset_id"
            />
          </el-select>
        </div>
        <InfoGrid
          v-if="selectedDataset"
          :items="datasetInfo"
        />
      </StepSection>
      <StepSection
        v-if="loading"
        index="02"
        title="处理数据问题"
      >
        <el-skeleton
          :rows="5"
          animated
        />
      </StepSection>
      <StepSection
        v-else-if="!steps.length"
        index="02"
        title="处理数据问题"
      >
        <el-button @click="loadOperations">
          重试加载处理项
        </el-button>
      </StepSection>
      <template v-else>
        <StepSection
          index="02"
          title="处理数据问题"
          :state="stepState(1)"
          collapsible
          :summary="`${enabledCount} 项处理已启用`"
        >
          <ChoiceGroup
            v-model="enabledOps"
            name="clean-op"
            multiple
            :options="opChoices"
            :disabled="busy || auth"
            aria-label="清洗处理项"
          >
            <template #extra="{ option }">
              <div
                v-if="option.raw.schema.length"
                class="check-params"
              >
                <label
                  v-for="param in option.raw.schema"
                  :key="param.name"
                  class="param-row"
                  :title="param.description"
                >
                  <span class="param-name">{{ paramLabel(option.raw, param) }}</span>
                  <el-select
                    v-if="param.choices"
                    v-model="option.raw.params[param.name]"
                    :disabled="busy || auth"
                  >
                    <el-option
                      v-for="choice in param.choices"
                      :key="choice"
                      :label="choiceLabel(option.raw, param, choice)"
                      :value="choice"
                    />
                  </el-select>
                  <el-select
                    v-else-if="isColumnParam(param)"
                    v-model="option.raw.params[param.name]"
                    multiple
                    collapse-tags
                    placeholder="选择列"
                    :disabled="busy || auth"
                  >
                    <el-option
                      v-for="column in inputColumns"
                      :key="column"
                      :label="column"
                      :value="column"
                    />
                  </el-select>
                  <el-input
                    v-else-if="param.type === 'array'"
                    :model-value="(option.raw.params[param.name] || []).join(', ')"
                    :disabled="busy || auth"
                    @update:model-value="setArrayParam(option.raw, param.name, $event)"
                  />
                  <el-checkbox
                    v-else-if="param.type === 'boolean'"
                    v-model="option.raw.params[param.name]"
                    :disabled="busy || auth"
                  />
                  <el-input-number
                    v-else
                    v-model="option.raw.params[param.name]"
                    :min="param.min ?? undefined"
                    :max="param.max ?? undefined"
                    :step="param.type === 'integer' ? 1 : 0.01"
                    :disabled="busy || auth"
                    controls-position="right"
                  />
                </label>
              </div>
            </template>
          </ChoiceGroup>
        </StepSection>
      </template>
      <StepSection
        index="03"
        title="确认导出文件名称"
        :state="stepState(2)"
        collapsible
        :summary="draft.output_name.trim() || '尚未命名'"
      >
        <div class="field">
          <span class="field-label">导出文件名称</span>
          <el-input
            id="clean-output-name"
            v-model="draft.output_name"
            maxlength="64"
            autocomplete="off"
            placeholder="导出文件名称"
            :disabled="busy || auth"
            aria-label="导出文件名称"
          />
        </div>
        <InfoGrid :items="confirmInfo" />
      </StepSection>
      <StepSection
        index="04"
        title="运行"
        :state="stepState(3)"
        sticky
      >
        <el-button
          data-testid="clean-run"
          class="run-button"
          type="primary"
          size="large"
          :loading="busy"
          :disabled="busy || auth || isRunning || !steps.length || !canRun"
          @click="submit"
        >
          开始清洗
        </el-button>
      </StepSection>
    </template>

    <template #after>
      <JobProgress
        title="清洗进度"
        test-id="clean-job"
        :job="cleaning.job"
        :text="progressText"
        retry-test-id="clean-retry"
        cancel-test-id="clean-cancel"
        :retry-disabled="auth || refreshing"
        :cancel-disabled="auth"
        @retry="retry"
        @cancel="cancel"
      />
      <JobResultPanel
        title="清洗结果"
        test-id="clean-result"
        :stats="resultStats"
        :error="outputError"
      >
        <template #notices>
          <p
            v-for="warning in result.summary?.warnings || []"
            :key="warning"
            class="validation"
          >
            {{ warning }}
          </p>
          <div
            v-if="saving || saveMessage"
            class="info-card save-card"
          >
            <div class="info-row">
              <span class="info-label">自动保存状态</span><span class="info-value">{{ saveMessage || '正在自动保存到数据集库' }}</span>
            </div>
          </div>
        </template>
        <el-collapse v-model="openSections">
          <el-collapse-item
            title="处理记录"
            name="stats"
          >
            <DataTable
              v-if="stats.length"
              :columns="cleanStatColumns"
              :rows="cleanStatRows"
              row-key="key"
              empty="暂无处理记录"
            />
          </el-collapse-item>
          <el-collapse-item
            title="清洗前后对比"
            name="diff"
          >
            <p class="section-note">
              按步骤展示处理前后的行数、缺失值、重复与标签分布变化；字段级变化见下方明细。
            </p>
            <DataTable
              v-if="diffRows.length"
              :columns="diffColumns"
              :rows="diffRows"
              row-key="key"
              empty="暂无对比数据"
            />
            <h3 class="subheading">
              字段变化明细
            </h3>
            <div class="diff-samples">
              <DataTable
                :columns="sampleColumns"
                :rows="sampleRows"
                row-key="key"
                empty="没有字段被修改"
              />
            </div>
          </el-collapse-item>
          <el-collapse-item
            title="清洗后预览"
            name="preview"
          >
            <DataTable
              v-if="preview"
              test-id="clean-preview"
              :columns="cleanPreviewColumns"
              :rows="cleanPreviewRows"
              row-key="commit_hash"
              empty="暂无预览数据"
            />
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
          </el-collapse-item>
        </el-collapse>
      </JobResultPanel>
      <section
        class="panel"
        data-pane="wide"
        aria-label="结果文件"
        data-testid="clean-files"
      >
        <div class="section-heading">
          <h2>结果文件</h2>
        </div>
        <OutputFiles
          :items="cleanFiles"
          @download="download"
        />
      </section>
    </template>
  </ToolWorkspace>
</template>

<script setup>
import { computed, onActivated, onDeactivated, reactive, ref, watch } from 'vue'
import ChoiceGroup from '../components/ChoiceGroup.vue'
import DataTable from '../components/DataTable.vue'
import InfoGrid from '../components/InfoGrid.vue'
import JobProgress from '../components/JobProgress.vue'
import JobResultPanel from '../components/JobResultPanel.vue'
import OutputFiles from '../components/OutputFiles.vue'
import StepRail from '../components/StepRail.vue'
import StepSection from '../components/StepSection.vue'
import ToolWorkspace from '../components/ToolWorkspace.vue'
import { cancelJob, fetchCleanOutput, getCleanOperations, getCleanPreview, getDatasets, getJob, getJobs, importStorageFiles, retryJob, runClean } from '../api'
import { cleaning } from '../utils/clean'
import { saveBlob } from '../utils/download'
import { scrollToResults } from '../utils/scroll'

defineOptions({ name: 'CleanTool' })
const DEFAULT_ENABLED_OPS = [
  'schema_validate', 'duplicate_drop', 'merge_commit_filter',
  'missing_value_handle', 'invalid_time_filter', 'unlabeled_handle',
  'label_validate', 'date_normalize'
]
const operations = ref([]), steps = ref([]), loading = ref(false)
const draft = reactive({ dataset_id: '', output_name: '' })
const inputColumns = ref([])
const datasets = ref([])
const busy = ref(false), auth = ref(false), error = ref(''), refreshing = ref(false), downloading = ref(false)
const saving = ref(false), saveMessage = ref('')
const stats = ref([]), preview = ref(null), outputError = ref('')
const openSections = ref([])
const previewPage = ref(1)
const previewSize = 12
const saveDraft = reactive({ name: '', repo_source: '' })
let timer, mounted = true, jobEpoch = 0, outputJob = '', epoch = 0, autoSaveJobId = ''
let activated = false
const result = computed(() => cleaning.job?.output_ref_json || {})
const resultStats = computed(() => {
  const data = result.value.summary || {}
  const removed = data.input_rows != null && data.output_rows != null ? data.input_rows - data.output_rows : null
  const modified = data.modified_rows
    ?? (stats.value.length ? stats.value.reduce((sum, step) => sum + (Number(step.modified_rows) || 0), 0) : null)
  return [
    { label: '输入行数', value: data.input_rows ?? '—' },
    { label: '输出行数', value: data.output_rows ?? '—' },
    { label: '删除行数', value: removed ?? '—' },
    { label: '修改行数', value: modified ?? '—' }
  ]
})
const hasInput = computed(() => Boolean(draft.dataset_id))
// 已完成步骤折叠后展示的关键信息，避免用户展开才知道当前配置。
const enabledCount = computed(() => steps.value.filter(step => step.enabled).length)
const canRun = computed(() => hasInput.value && Boolean(draft.output_name.trim()))
// 顶部步骤轨道：以选定数据集为起点，输出命名完成即视为配置就绪。
const railSteps = [
  { title: '选择输入', note: '数据集' },
  { title: '处理问题', note: '处理项' },
  { title: '命名输出', note: '输出名称' },
  { title: '运行', note: '开始清洗' }
]
const activeStep = computed(() => {
  if (isRunning.value || cleaning.job?.status === 'success') return 3
  if (!hasInput.value) return 0
  if (!draft.output_name.trim()) return 2
  return 1
})
function stepState(index) {
  if (cleaning.job?.status === 'success') return 'done'
  if (index < activeStep.value) return 'done'
  return index === activeStep.value ? 'current' : 'upcoming'
}
const selectedDataset = computed(() => datasets.value.find(item => item.dataset_id === draft.dataset_id))
const datasetInfo = computed(() => {
  const data = selectedDataset.value
  if (!data) return []
  return [
    { label: '数据集名称', value: data.name },
    { label: '来源类型', value: sourceTypeLabel(data.source_type) },
    { label: '来源仓库', value: data.repo_source || data.repo_name || data.source_url || '未提供' },
    { label: '分支', value: data.branch || '默认分支' },
    { label: 'HEAD', value: shortHash(data.head_hash), mono: true },
    { label: '样本数', value: `${data.sample_count ?? 0} 条` },
    { label: '正样本', value: `${data.pos_count ?? 0} 条` },
    { label: '负样本', value: `${data.neg_count ?? 0} 条` },
    { label: '未标注', value: `${unlabeledCount(data)} 条` },
    { label: '时间范围', value: formatRange(data.time_start, data.time_end) },
    { label: '状态', value: statusText(data.status) },
    { label: '创建时间', value: formatTime(data.created_at) }
  ]
})
const confirmInfo = computed(() => {
  const data = selectedDataset.value
  return [
    { label: '输入数据集', value: data?.name || '未选择' },
    { label: '来源仓库', value: data?.repo_source || data?.repo_name || data?.source_url || '未提供' },
    { label: '分支', value: data?.branch || '默认分支' },
    { label: '样本数', value: `${data?.sample_count ?? 0} 条` },
    { label: '正样本', value: `${data?.pos_count ?? 0} 条` },
    { label: '负样本', value: `${data?.neg_count ?? 0} 条` },
    { label: '未标注', value: `${data ? unlabeledCount(data) : 0} 条` },
    { label: '时间范围', value: formatRange(data?.time_start, data?.time_end) },
    { label: '启用处理', value: enabledStepsText.value, span: true },
    { label: '输出', value: '清洗后数据集' },
    { label: '保存方式', value: '任务成功后自动保存到数据集库' }
  ]
})
watch(() => draft.dataset_id, id => {
  const target = datasets.value.find(item => item.dataset_id === id)
  draft.output_name = target ? `${target.name}清洗后` : ''
})
const operationSummaries = {
  schema_validate: '必选 · 保证后续步骤能正确读取数据',
  duplicate_drop: '删除内容完全相同的提交记录',
  merge_commit_filter: '过滤合并提交，只保留实际代码提交',
  missing_value_handle: '决定空值保留、填充还是删除',
  invalid_time_filter: '删除时间缺失或格式错误的提交',
  unlabeled_handle: '决定未标注样本如何处理',
  outlier_filter: '识别明显偏离常规范围的数值',
  label_validate: '校验缺陷标签只能为 1、0 或空',
  text_clean: '清理提交说明中的空白和异常字符',
  type_convert: '把指定列统一成系统需要的类型',
  date_normalize: '把提交时间统一成标准格式',
  text_normalize: '统一文本大小写与空白格式',
  category_normalize: '合并含义相同的类别值',
  derive_basic_fields: '派生提交长度、父提交数等展示列'
}
const paramLabels = {
  strategy: '处理方式',
  method: '识别方式',
  columns: '需要处理的列',
  missing_value_handle: { strategy: '缺失值处理方式' },
  unlabeled_handle: { strategy: '未标注样本处理' },
  outlier_filter: { method: '异常值识别方式' },
  type_convert: { columns: '需要统一类型的列' },
  derive_basic_fields: { columns: '需要派生的展示列' },
  text_normalize: { columns: '需要规范化的文本列' },
  category_normalize: { columns: '需要规范化的类别列' },
  text_clean: { columns: '需要清洗的文本列' }
}
const choiceLabels = {
  keep: '保留',
  fill: '自动填充',
  exclude: '删除',
  warn: '仅标记警告',
  iqr: '四分位距',
  zscore: '标准差',
  missing_value_handle: { keep: '保留空值', fill: '自动填充', exclude: '删除含空值行' },
  unlabeled_handle: { keep: '保留未标注', exclude: '删除未标注', warn: '仅标记警告' },
  outlier_filter: { iqr: '四分位距', zscore: '标准差' }
}
function operationSummary(step) {
  return operationSummaries[step.op] || step.description || '按系统规则处理数据'
}
function paramLabel(step, param) {
  return paramLabels[step.op]?.[param.name] || paramLabels[param.name] || param.description || param.name
}
function choiceLabel(step, param, choice) {
  return choiceLabels[step.op]?.[choice] || choiceLabels[choice] || choice
}
function isColumnParam(param) {
  return param.name === 'columns' && inputColumns.value.length > 0
}
// 处理项走统一的 ChoiceGroup 卡片，页面不再手写多选结构。
const opChoices = computed(() => steps.value.map(step => ({
  key: step.op,
  label: operation(step.op).name || step.op,
  summary: operationSummary(step),
  locked: step.locked,
  disabled: step.locked,
  raw: step
})))
const enabledOps = computed({
  get: () => steps.value.filter(step => step.enabled).map(step => step.op),
  set: list => steps.value.forEach(step => { step.enabled = step.locked || list.includes(step.op) })
})
const enabledSteps = computed(() => steps.value.filter(step => step.enabled))
function setArrayParam(step, name, value) {
  step.params[name] = String(value).split(/[,，]/).map(item => item.trim()).filter(Boolean)
}
const enabledStepsText = computed(() => enabledSteps.value.length
  ? `${enabledSteps.value.length} 项，${enabledSteps.value.map(step => operation(step.op).name || step.op).join('，')}`
  : '未启用')
function formatTime(value) {
  if (!value) return '未提供'
  return String(value).replace('T', ' ').replace(/\.\d+Z?$/, '').replace('Z', '').slice(0, 16)
}
function formatRange(start, end) {
  if (!start && !end) return '未提供'
  return `${formatTime(start)} 至 ${formatTime(end)}`
}
function shortHash(value) {
  return value ? String(value).slice(0, 10) : '未提供'
}
function sourceTypeLabel(value) {
  return { git_repo: 'Git 仓库', public_dataset: '开源数据集' }[value] || value || '未提供'
}
function statusText(value) {
  return { ready: '可用', collecting: '收集中', failed: '失败', archived: '已归档' }[value] || value || '未知'
}
function unlabeledCount(dataset) {
  return Math.max(0, (dataset.sample_count ?? 0) - (dataset.pos_count ?? 0) - (dataset.neg_count ?? 0))
}
// 结果文件只展示清洗后的那一份数据，CSV/Excel 由用户下载时选择，避免提前重复保存。
const cleanFiles = computed(() => {
  const csv = (result.value.outputs || []).find(item => item.name.endsWith('.csv'))
  if (!csv) return []
  return [{
    name: csv.name,
    label: '清洗后数据',
    size: csv.size,
    testid: 'clean-download-dataset',
    formats: [
      { label: 'CSV', ext: 'csv', name: csv.name },
      { label: 'Excel', ext: 'xlsx', name: csv.name }
    ],
    disabled: auth.value || downloading.value
  }]
})
const cleanStatColumns = [
  { key: 'op', label: '步骤' },
  { key: 'rows_before', label: '处理前行数', align: 'right' },
  { key: 'rows_after', label: '处理后行数', align: 'right' },
  { key: 'removed', label: '删除行数', align: 'right' },
  { key: 'modified', label: '修改行数', align: 'right' },
  { key: 'positive', label: '正样本', align: 'right' },
  { key: 'negative', label: '负样本', align: 'right' },
  { key: 'unlabeled', label: '未标注', align: 'right' }
]
function labelDistribution(value) {
  return {
    positive: value?.positive ?? value?.['1'] ?? 0,
    negative: value?.negative ?? value?.['0'] ?? 0,
    unlabeled: value?.unlabeled ?? value?.null ?? 0
  }
}
const cleanStatRows = computed(() => stats.value.map((step, index) => {
  const key = step.step || step.op
  const dist = labelDistribution(step.label_dist_after || step.label_dist)
  return {
    op: operation(key).name || key,
    key: `${key}-${index}`,
    rows_before: step.rows_before,
    rows_after: step.rows_after,
    removed: step.removed_rows ?? step.removed,
    modified: step.modified_rows ?? step.modified,
    positive: dist.positive,
    negative: dist.negative,
    unlabeled: dist.unlabeled
  }
}))
const diffColumns = [
  { key: 'step', label: '步骤' },
  { key: 'rows', label: '行数变化', align: 'right' },
  { key: 'removed', label: '删除', align: 'right' },
  { key: 'modified', label: '修改', align: 'right' },
  { key: 'missing', label: '缺失值变化', align: 'right' },
  { key: 'duplicate', label: '重复变化', align: 'right' },
  { key: 'labels', label: '正/负/未标注变化' }
]
function countText(before, after) {
  if (before == null || after == null) return '—'
  return `${before} → ${after}`
}
function labelText(value) {
  const dist = labelDistribution(value)
  return `${dist.positive}/${dist.negative}/${dist.unlabeled}`
}
const diffRows = computed(() => stats.value.map((step, index) => {
  const key = step.step || step.op
  return {
    key: `${key}-diff-${index}`,
    step: operation(key).name || key,
    rows: `${step.rows_before ?? '—'} → ${step.rows_after ?? '—'}`,
    removed: step.removed_rows ?? step.removed ?? 0,
    modified: step.modified_rows ?? step.modified ?? 0,
    missing: countText(step.missing_before, step.missing_after),
    duplicate: countText(step.duplicate_before, step.duplicate_after),
    labels: `${labelText(step.label_dist_before)} → ${labelText(step.label_dist_after)}`
  }
}))
const sampleColumns = [
  { key: 'step', label: '步骤' },
  { key: 'hash', label: '提交', mono: true },
  { key: 'changes', label: '字段变化' }
]
function changeValue(value) {
  if (value == null || value === '') return '空'
  return String(value)
}
const sampleRows = computed(() => stats.value.flatMap((step, index) => {
  const name = operation(step.step || step.op).name || step.step || step.op
  return (step.modified_samples || []).map((sample, sampleIndex) => ({
    key: `${step.step || step.op}-${index}-${sampleIndex}`,
    step: name,
    hash: sample.commit_hash,
    changes: Object.entries(sample.changes || {})
      .map(([field, pair]) => `${field}: ${changeValue(pair?.before)} → ${changeValue(pair?.after)}`)
      .join('；')
  }))
}))
const cleanPreviewColumns = computed(() => (preview.value?.columns || []).map(key => ({ key, label: key, mono: key === 'commit_hash' })))
const cleanPreviewRows = computed(() => (preview.value?.preview || []).map(row => ({
  ...row,
  is_bug_inducing: row.is_bug_inducing == null || row.is_bug_inducing === '' ? '未标注' : row.is_bug_inducing
})))
const isRunning = computed(() => ['queued', 'running'].includes(cleaning.job?.status))
const phaseLabel = computed(() => {
  const phase = cleaning.job?.current_item
  if (!phase) return '准备中'
  if (phase === 'publish') return '发布结果'
  if (phase === 'parse_input') return '读取输入'
  return operation(phase).name || phase
})
const progressText = computed(() => {
  const status = cleaning.job?.status
  if (!status) return '当前未开始，选择数据集后开始清洗'
  if (status === 'queued') return '当前正在排队等待执行'
  if (status === 'running') return `当前正在${phaseLabel.value}`
  if (status === 'success') return '当前清洗已完成'
  if (status === 'failed') return '当前清洗失败，可重试原任务'
  if (status === 'cancelled') return '当前清洗已取消'
  return ''
})
const operation = op => operations.value.find(item => item.op === op) || {}
function message(err) {
  if (err.code === 40100) { auth.value = true; return '登录已失效，请重新登录' }
  return err.code === 50000 ? '清洗服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
async function loadOperations() {
  loading.value = true
  try {
    const data = await getCleanOperations()
    if (!Array.isArray(data.operations) || !data.operations.length) throw new Error('操作注册表响应不完整')
    operations.value = data.operations
    inputColumns.value = data.operations[0]?.input_schema?.columns || []
    steps.value = data.operations.map(item => ({
      op: item.op,
      description: item.description || '',
      group: item.group || 'clean',
      enabled: item.op === 'schema_validate' || DEFAULT_ENABLED_OPS.includes(item.op),
      locked: (item.order_constraints || []).some(constraint => constraint.type === 'first'),
      schema: item.params_schema || [],
      params: Object.fromEntries((item.params_schema || []).map(param => [param.name, param.default]))
    }))
  } catch (err) { error.value = message(err) }
  finally { loading.value = false }
}
async function loadSources() {
  try {
    const data = await getDatasets({ size: 100, status: 'ready' })
    datasets.value = data.items
    // 默认选中最新可用数据集，命名步骤会随之自动填好。
    if (!datasets.value.some(item => item.dataset_id === draft.dataset_id)) {
      draft.dataset_id = datasets.value[0]?.dataset_id || ''
    }
  } catch (err) { error.value = message(err) }
}
function resetOutputs() {
  epoch++; outputJob = ''; stats.value = []; preview.value = null; outputError.value = ''
  openSections.value = []; previewPage.value = 1
}
async function submit() {
  if (busy.value || auth.value || isRunning.value || !steps.value.length || !canRun.value) return
  busy.value = true; error.value = ''; saveMessage.value = ''
  try {
    const outputName = draft.output_name.trim()
    const config = {
      mode: 'apply',
      steps: steps.value.map(step => ({ op: step.op, enabled: step.enabled, params: { ...step.params } })),
      format: 'csv',
      dataset_id: draft.dataset_id,
      output_name: outputName
    }
    const accepted = await runClean(config, [])
    if (!accepted?.job_id || !['queued', 'running', 'success', 'failed'].includes(accepted.status)) throw new Error('清洗任务响应不完整')
    resetOutputs()
    cleaning.request = config
    cleaning.job = accepted
    scrollToResults()
    autoSaveJobId = accepted.job_id
    saveDraft.name = outputName
    saveDraft.repo_source = selectedDataset.value?.repo_source || ''
    await refreshJob()
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
async function saveAutomatically() {
  const id = cleaning.job?.job_id
  if (!id || !result.value.outputs?.length || saving.value) return
  saving.value = true
  saveMessage.value = ''
  try {
    const csvName = result.value.outputs.find(item => item.name.endsWith('.csv'))?.name
    if (!csvName) throw new Error('未找到清洗数据文件')
    const manifest = result.value.outputs.find(item => item.name.endsWith('.manifest.json'))?.name || csvName.replace(/\.csv$/, '.manifest.json')
    const blobs = await Promise.all([fetchCleanOutput(id, csvName), fetchCleanOutput(id, manifest)])
    const response = await importStorageFiles([new File([blobs[0]], csvName), new File([blobs[1]], manifest)], {
      create_dataset: { name: saveDraft.name, repo_source: saveDraft.repo_source }
    })
    if (!response?.items?.length || !response.summary) throw new Error('导入响应不完整')
    if (response.summary.rejected || response.items.some(item => item.status === 'rejected')) {
      saveMessage.value = '自动保存未完成，请检查导入结果'
      return
    }
    saveMessage.value = `已保存到数据集库，名称 ${saveDraft.name}`
    await loadSources()
  } catch (err) { saveMessage.value = `自动保存未完成，${message(err)}` }
  finally { saving.value = false }
}
async function loadOutputs(id) {
  if (outputJob === id) return
  const ownEpoch = epoch, reference = result.value
  try {
    const statsName = reference.outputs.find(item => item.name.endsWith('_steps_stats.json'))?.name
    if (!statsName) throw new Error('输出缺少处理记录文件')
    const statsBlob = await fetchCleanOutput(id, statsName)
    const parsedStats = JSON.parse(await statsBlob.text())
    const stagedPreview = await getCleanPreview(id, { page: 1, size: previewSize })
    if (!mounted || ownEpoch !== epoch || cleaning.job?.job_id !== id) return
    stats.value = parsedStats; preview.value = stagedPreview; previewPage.value = stagedPreview.page || 1
    openSections.value = [
      parsedStats?.length ? 'stats' : '',
      parsedStats?.length ? 'diff' : '',
      stagedPreview?.total ? 'preview' : ''
    ].filter(Boolean)
    outputJob = id; outputError.value = ''
  } catch (err) { if (mounted && ownEpoch === epoch) outputError.value = message(err) }
}
// 清洗后预览按页读取全部行，避免只展示前几条。
async function loadPreview(page = 1) {
  const id = cleaning.job?.job_id
  if (!id) return
  try {
    const data = await getCleanPreview(id, { page, size: previewSize })
    if (cleaning.job?.job_id !== id) return
    preview.value = data
    previewPage.value = data.page || page
  } catch (err) { if (mounted) outputError.value = message(err) }
}
async function refreshJob() {
  if (!cleaning.job?.job_id || refreshing.value || auth.value) return
  clearTimeout(timer); refreshing.value = true
  const id = cleaning.job.job_id, token = ++jobEpoch
  try {
    const data = await getJob(id)
    if (!mounted || token !== jobEpoch || cleaning.job?.job_id !== id) return
    if (data.kind !== 'clean' || !['queued', 'running', 'success', 'failed', 'cancelled'].includes(data.status)) throw new Error('任务响应不完整')
    cleaning.job = data
    if (data.status === 'success') await loadOutputs(id)
    if (data.status === 'success' && id === autoSaveJobId) {
      autoSaveJobId = ''
      await saveAutomatically()
    }
  } catch (err) { if (mounted && token === jobEpoch && cleaning.job?.job_id === id) error.value = message(err) }
  finally {
    refreshing.value = false
    if (mounted && token === jobEpoch && ['queued', 'running'].includes(cleaning.job?.status)) timer = setTimeout(refreshJob, 1500)
  }
}
async function retry() {
  try {
    const id = cleaning.job.job_id
    await retryJob(id)
    resetOutputs(); cleaning.job = await getJob(id)
    autoSaveJobId = id
    saveMessage.value = ''
    await refreshJob()
  } catch (err) { error.value = message(err) }
}
async function cancel() {
  try {
    const id = cleaning.job.job_id
    await cancelJob(id)
    jobEpoch++; clearTimeout(timer)
    cleaning.job = await getJob(id)
    autoSaveJobId = ''
  } catch (err) { error.value = message(err) }
}
async function download(item) {
  const name = typeof item === 'string' ? item : item.name
  const format = typeof item === 'string' ? 'csv' : (item.format || 'csv')
  downloading.value = true
  try {
    const blob = await fetchCleanOutput(cleaning.job.job_id, name, format)
    saveBlob(blob, format === 'xlsx' ? name.replace(/\.csv$/, '.xlsx') : name)
  }
  catch (err) { error.value = message(err) }
  finally { downloading.value = false }
}
onActivated(async () => {
  mounted = true; jobEpoch++
  // 二次进入保留已选数据集、处理项与输出名，只续接任务进度。
  if (activated) { await refreshJob(); return }
  activated = true
  await Promise.all([loadOperations(), loadSources()])
  if (!cleaning.job) {
    try { const data = await getJobs({ kind: 'clean', size: 1 }); cleaning.job = data.items?.[0] || null }
    catch (err) { error.value = message(err) }
  }
  if (cleaning.request) {
    const source = datasets.value.find(item => item.dataset_id === cleaning.request.dataset_id)
    draft.output_name = cleaning.request.output_name || (source ? `${source.name}清洗后` : '')
    saveDraft.name = draft.output_name
    saveDraft.repo_source = source?.repo_source || ''
    if (Array.isArray(cleaning.request.steps)) {
      steps.value = steps.value.map(step => {
        const saved = cleaning.request.steps.find(item => item.op === step.op)
        return saved ? { ...step, enabled: Boolean(saved.enabled), params: { ...step.params, ...(saved.params || {}) } } : step
      })
    }
  }
  await refreshJob()
})
onDeactivated(() => { mounted = false; clearTimeout(timer) })
</script>

<style scoped>
.section-note { margin: 0 0 var(--ui-space-3); color: var(--ui-text-muted); font-size: var(--ui-font-hint); }
.subheading { margin: var(--ui-space-4) 0 var(--ui-space-2); font-size: var(--ui-font-body); font-weight: 600; }
.diff-samples { max-height: 320px; overflow: auto; }
.pagination { margin-top: 16px; justify-content: flex-end; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: var(--ui-font-hint); }
</style>
