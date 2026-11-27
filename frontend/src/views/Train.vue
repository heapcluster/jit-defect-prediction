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
        :summary="selectedSource?.label || '尚未选择清洗结果'"
      >
        <div class="field">
          <span class="field-label">已清洗数据</span>
          <el-select
            id="train-source"
            v-model="draft.source_id"
            :placeholder="sources.length ? '请选择清洗结果中的训练数据' : '暂无清洗结果，请先完成数据清洗'"
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
          正在读取清洗结果…
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
        index="02"
        title="选择架构"
        :state="stepState(1)"
        collapsible
        :summary="lineLabel(line)"
      >
        <ChoiceGroup
          v-model="line"
          name="train-line"
          :options="lineChoices"
          :disabled="busy || auth"
          @change="loadAlgorithms"
        />
      </StepSection>
      <StepSection
        index="03"
        title="选择算法"
        :state="stepState(2)"
        collapsible
        :summary="selected.length ? `${selected.length} 个算法：${selected.join('、')}` : '尚未选择算法'"
      >
        <el-skeleton
          v-if="algoLoading"
          :rows="3"
          animated
        />
        <ChoiceGroup
          v-else-if="visibleAlgorithms.length"
          v-model="selected"
          name="train-algo"
          multiple
          :options="algoChoices"
          :disabled="busy || auth"
        >
          <template #extra="{ option }">
            <div
              v-if="option.raw.hyperparams_schema?.length"
              class="check-params"
            >
              <label
                v-for="param in option.raw.hyperparams_schema"
                :key="param.name"
                class="param-row"
                :title="param.description"
              >
                <span class="param-name">{{ hyperparamLabel(option.key, param) }}</span>
                <el-select
                  v-if="param.choices"
                  v-model="draft.hyperparams[option.key][param.name]"
                  :disabled="busy || auth"
                >
                  <el-option
                    v-for="choice in param.choices"
                    :key="choice"
                    :label="hyperparamChoiceLabel(choice)"
                    :value="choice"
                  />
                </el-select>
                <el-input-number
                  v-else
                  v-model="draft.hyperparams[option.key][param.name]"
                  :min="param.min ?? undefined"
                  :max="param.max ?? undefined"
                  :step="param.type === 'integer' ? 1 : 0.01"
                  :disabled="busy || auth"
                  :aria-label="hyperparamLabel(option.key, param)"
                  controls-position="right"
                />
              </label>
            </div>
          </template>
        </ChoiceGroup>
        <p
          v-if="!algoLoading && !visibleAlgorithms.length"
          class="status-line"
        >
          暂无可用的算法，请稍后重试
        </p>
      </StepSection>
      <StepSection
        index="04"
        title="划分训练与测试集"
        :state="stepState(3)"
        collapsible
        :summary="draft.split_mode === 'ratio' ? `训练 ${Math.round(trainRatio * 100)}% / 测试 ${Math.round(testRatio * 100)}%` : '按时间切分'"
      >
        <template #extra>
          <el-tag class="step-tag">
            {{ draft.split_mode === 'ratio' ? `训练 ${Math.round(trainRatio * 100)}%` : '按时间切分' }}
          </el-tag>
        </template>
        <ChoiceGroup
          v-model="draft.split_mode"
          name="train-split"
          :options="splitChoices"
          :disabled="busy || auth"
          list-class="split-list"
        />
        <div class="fields param-grid">
          <div
            v-if="draft.split_mode === 'ratio'"
            class="field"
          >
            <span class="field-label">训练 {{ Math.round(trainRatio * 100) }}% / 测试 {{ Math.round(testRatio * 100) }}%</span>
            <el-slider
              v-model="trainRatio"
              :min="0.5"
              :max="0.9"
              :step="0.05"
              show-stops
              :disabled="busy || auth"
              aria-label="训练比例"
            />
          </div>
          <div
            v-else
            class="field"
          >
            <span class="field-label">时间边界（UTC）</span>
            <el-date-picker
              v-model="draft.time_boundary"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm"
              placeholder="选择训练与测试的分界时间"
              :disabled="busy || auth"
            />
          </div>
          <div class="field">
            <span class="field-label">判定阈值 {{ thresholdText }}</span>
            <el-slider
              v-model="draft.threshold"
              :min="0.05"
              :max="0.95"
              :step="0.01"
              :disabled="busy || auth"
              aria-label="判定阈值"
            />
          </div>
          <div class="field">
            <span class="field-label">随机种子</span>
            <el-input-number
              v-model="draft.seed"
              :min="0"
              :step="1"
              :disabled="busy || auth"
              controls-position="right"
              aria-label="随机种子"
            />
          </div>
        </div>
        <InfoGrid :items="splitInfo">
          <p
            v-if="timeError"
            class="validation"
          >
            {{ timeError }}
          </p>
          <p
            v-if="thresholdError"
            class="validation"
          >
            {{ thresholdError }}
          </p>
          <p
            v-if="seedError"
            class="validation"
          >
            {{ seedError }}
          </p>
        </InfoGrid>
      </StepSection>
      <StepSection
        index="05"
        title="运行"
        :state="stepState(4)"
        sticky
      >
        <el-button
          data-testid="train-run"
          class="run-button"
          type="primary"
          size="large"
          :loading="busy"
          :disabled="busy || auth || isRunning || !canTrain"
          @click="submit"
        >
          开始训练
        </el-button>
      </StepSection>
    </template>
    <template #after>
      <JobProgress
        title="训练进度"
        test-id="train-job"
        :job="training.job"
        :text="progressText"
        retry-test-id="train-retry"
        cancel-test-id="train-cancel"
        :retry-disabled="auth || refreshing"
        :cancel-disabled="auth"
        @retry="retry"
        @cancel="cancel"
      />
      <section
        class="panel"
        data-pane="wide"
        aria-label="训练结果"
        data-testid="train-result"
      >
        <div class="section-heading">
          <h2>训练结果</h2>
        </div>
        <StatGrid :items="resultStats" />
        <p
          v-for="warning in summary.warnings || []"
          :key="warning"
          class="validation"
        >
          {{ warning }}
        </p>
        <el-alert
          v-if="outputError"
          :title="outputError"
          type="error"
          :closable="false"
        />
        <div
          v-if="registerText"
          class="info-card save-card"
        >
          <div class="info-row">
            <span class="info-label">保存状态</span><span class="info-value">{{ registerText }}</span>
          </div>
        </div>
      </section>
      <section
        class="panel"
        data-pane="wide"
        aria-label="结果文件"
        data-testid="train-files"
      >
        <div class="section-heading">
          <h2>结果文件</h2>
        </div>
        <OutputFiles
          :items="trainFiles"
          @download="item => download(item.name)"
        />
      </section>
    </template>
  </ToolWorkspace>
</template>

<script setup>
import { computed, onActivated, onDeactivated, reactive, ref, watch } from 'vue'
import ChoiceGroup from '../components/ChoiceGroup.vue'
import InfoGrid from '../components/InfoGrid.vue'
import JobProgress from '../components/JobProgress.vue'
import OutputFiles from '../components/OutputFiles.vue'
import StatGrid from '../components/StatGrid.vue'
import StepRail from '../components/StepRail.vue'
import StepSection from '../components/StepSection.vue'
import ToolWorkspace from '../components/ToolWorkspace.vue'
import { cancelJob, fetchTrainOutput, getAlgorithms, getJob, getJobs, retryJob, runTrain } from '../api'
import { artifactSources, loadArtifactJobs, materializeArtifact } from '../utils/artifacts'
import { training } from '../utils/train'
import { saveBlob } from '../utils/download'
import { scrollToResults } from '../utils/scroll'

defineOptions({ name: 'TrainTool' })
const hasInput = computed(() => Boolean(draft.source_id))
const line = ref('expert'), algorithms = ref([]), algoLoading = ref(false), selected = ref([])
const draft = reactive({
  source_id: '',
  ratio: 0.7,
  split_mode: 'ratio',
  time_boundary: '',
  threshold: 0.5,
  seed: 42,
  hyperparams: {}
})
const trainRatio = computed({
  get: () => draft.ratio,
  set: value => { draft.ratio = Number(value) }
})
const thresholdText = computed(() => Number(draft.threshold || 0).toFixed(2))
const splitSummaryText = computed(() => draft.split_mode === 'ratio'
  ? `按比例随机切分，${Math.round(trainRatio.value * 100)}% 训练 / ${Math.round(testRatio.value * 100)}% 测试`
  : `按时间顺序切分，边界 ${draft.time_boundary || '未选择'} UTC`)
const testRatio = computed(() => Number((1 - draft.ratio).toFixed(2)))
const sourceJobs = reactive({ items: [], total: 0, page: 1 })
const sources = computed(() => artifactSources(sourceJobs.items, ['.csv', '.xlsx']))
const selectedSource = computed(() => sources.value.find(item => item.value === draft.source_id))
const selectedJob = computed(() => sourceJobs.items.find(job => job.job_id === selectedSource.value?.job_id))
const sourcesLoading = ref(false), sourcesError = ref('')
const busy = ref(false), auth = ref(false), error = ref(''), refreshing = ref(false), downloading = ref(false)
const outputError = ref('')
let timer, mounted = true, jobEpoch = 0
let activated = false
const result = computed(() => training.job?.output_ref_json || {})
const summary = computed(() => result.value.summary || {})
// 训练产物只保留训练集、测试集与成功算法的 .pkl；内部归档文件不在结果区展示。
const trainFiles = computed(() => (result.value.outputs || [])
  .filter(item => item.name.endsWith('.pkl') || item.name.endsWith('.csv'))
  .map(item => ({
    ...item,
    label: item.name.endsWith('.pkl')
      ? '模型文件'
      : item.name.includes('train_trainset')
        ? '训练集'
        : item.name.includes('train_testset')
          ? '测试集（预测输入）'
          : '数据文件',
    testid: `train-download-${item.name}`,
    disabled: auth.value || downloading.value
  })))
const isRunning = computed(() => ['queued', 'running'].includes(training.job?.status))
const algoLabels = {
  lr: '逻辑回归', rf: '随机森林', xgb: 'XGBoost', lgbm: 'LightGBM', et: '极端随机树',
  svm: '支持向量机', nb: '朴素贝叶斯', dt: '决策树', knn: 'k 近邻',
  mlp: '单隐藏层感知机', mlp_deep: '多层感知机', tabnet: 'TabNet'
}
const algoLabel = algo => algoLabels[algo] || algo
// 悬停说明：卡片上只留简短名称，括号里的口径和用途放到提示里
const algoTips = {
  lr: '线性基线，可解释性最好，适合先跑通流程再对比其他模型。',
  rf: '多棵决策树投票的集成模型，稳健、抗过拟合。',
  xgb: '梯度提升树，通常精度最高，训练耗时也最长。',
  lgbm: '轻量梯度提升树，速度快、内存占用低。',
  et: '极端随机树，随机分裂的树集成，训练快。',
  svm: 'RBF 核支持向量机，适合中小规模样本。',
  nb: '高斯朴素贝叶斯，假设特征独立，作极简基线。',
  dt: '单棵决策树，规则直观，容易过拟合。',
  knn: 'k 近邻，按距离投票，对特征尺度敏感。',
  mlp: '单隐藏层基础神经网络，仅用于历史模型对比。',
  mlp_deep: '3 层隐藏层并带早停的深度神经网络。',
  tabnet: '带注意力机制的表格网络，可解释的深度学习模型。'
}
const algoTip = item => `${item.family || '模型'}｜${algoTips[item.algo] || item.description || algoLabel(item.algo)}`
const hyperparamLabels = {
  'lr__C': '正则化强度（C）',
  'lr__max_iter': '最大迭代次数',
  n_estimators: '树的数量',
  max_depth: '树的最大深度',
  min_samples_leaf: '叶节点最少样本数',
  learning_rate: '学习率',
  subsample: '行采样比例',
  colsample_bytree: '建树列采样比例',
  num_leaves: '叶子数上限',
  'svm__C': '惩罚系数（C）',
  'svm__gamma': 'RBF 核系数',
  var_smoothing: '方差平滑项',
  'knn__n_neighbors': '近邻数（k）',
  'mlp__max_iter': '最大迭代轮数',
  'mlp__alpha': 'L2 正则系数',
  'mlp__n_iter_no_change': '早停耐心轮数',
  'mlp__validation_fraction': '早停验证比例',
  'tabnet__max_epochs': '最大训练轮数',
  'tabnet__patience': '早停耐心轮数',
  'tabnet__validation_fraction': '早停验证比例'
}
const algoHyperparamLabels = {
  xgb: { n_estimators: '提升轮数' },
  lgbm: { n_estimators: '提升轮数' }
}
const hyperparamChoiceLabels = {
  scale: '按数据缩放',
  auto: '按特征数自动'
}
function hyperparamLabel(algo, param) {
  return algoHyperparamLabels[algo]?.[param.name] || hyperparamLabels[param.name] || param.description || param.name
}
function hyperparamChoiceLabel(choice) {
  return hyperparamChoiceLabels[choice] || choice
}
// 只保留一种多层感知机，避免同一网络出现两个入口
const visibleAlgorithms = computed(() => algorithms.value.filter(item => item.algo !== 'mlp'))
const lineOptions = [
  {
    value: 'expert',
    label: '专家特征',
    note: 'Kamei 14 维',
    description: '基于代码变更度量（Kamei 14 维工程特征）训练，特征在训练时从绑定的数据来源现算。'
  },
  {
    value: 'semantic',
    label: '语义特征',
    note: 'CodeBERT 768 维',
    description: '基于提交文本的冻结头 CodeBERT 768 维语义向量训练，需要可读的仓库提交文本。'
  }
]
const lineLabel = line => lineOptions.find(item => item.value === line)?.label || '专家特征'
const lineChoices = computed(() => lineOptions.map(item => ({
  key: item.value,
  label: item.label,
  note: item.note,
  tip: item.description
})))
const algoChoices = computed(() => visibleAlgorithms.value.map(item => ({
  key: item.algo,
  label: algoLabel(item.algo),
  tip: algoTip(item),
  summary: algoTip(item),
  badge: item.enabled ? '默认' : '',
  testid: 'train-algo',
  raw: item
})))
const splitChoices = [
  { key: 'ratio', label: '按比例切分', tip: '随机打乱后按比例切出测试集，适合常规抽样评估。' },
  { key: 'time', label: '按时间顺序切分', tip: '按提交时间划一条边界：边界前训练、边界后测试，模拟上线后的时序评估。' }
]
const sourceInfo = computed(() => [
  { label: '清洗任务', value: selectedJob.value?.label || '未提供' },
  { label: '样本规模', value: selectedJob.value?.summary || '未提供' },
  { label: '数据文件', value: selectedSource.value.name, mono: true },
  { label: '清单文件', value: selectedSource.value.companions?.[0] || '随数据一起提交', mono: true },
  { label: '生成时间', value: formatTime(selectedJob.value?.created_at) },
  { label: '任务状态', value: selectedJob.value?.statusLabel || '成功' }
])
const splitInfo = computed(() => [
  { label: '训练与测试', value: splitSummaryText.value, span: true },
  { label: '输入数据', value: selectedJob.value?.label || '未选择' },
  { label: '样本规模', value: selectedJob.value?.summary || '未提供' },
  { label: '模型类型', value: lineLabel(line.value) },
  { label: '已选算法', value: selectedAlgoText.value },
  { label: '输出', value: '训练集、测试集与每个成功算法的 .pkl 模型文件', span: true }
])
const resultStats = computed(() => [
  { label: '输入样本', value: summary.value.input_rows ?? '—' },
  { label: '训练样本', value: summary.value.train_rows ?? '—' },
  { label: '测试样本', value: summary.value.test_rows ?? '—' },
  { label: '成功模型', value: successText.value }
])
const phaseLabel = computed(() => {
  const status = training.job?.status
  if (!status) return '未开始'
  if (status === 'success') return '已完成'
  if (['failed', 'cancelled'].includes(status)) return '已结束'
  const phase = training.job?.current_item
  return phase ? algoLabel(phase) : '准备中'
})
const successText = computed(() => summary.value.success_count == null
  ? '—'
  : `${summary.value.success_count} / ${(result.value.models || []).length}`)
const progressText = computed(() => {
  const status = training.job?.status
  if (!status) return '当前未开始，选择输入与算法后开始训练'
  if (status === 'queued') return '当前正在排队等待执行'
  if (status === 'running') {
    return phaseLabel.value === '准备中' ? '当前正在准备训练数据' : `当前正在训练${phaseLabel.value}`
  }
  if (status === 'success') return '当前训练已完成'
  if (status === 'failed') return '当前训练失败，可重试原任务'
  if (status === 'cancelled') return '当前训练已取消'
  return ''
})
const selectedAlgoText = computed(() => selected.value.length
  ? `${selected.value.length} 个，${selected.value.map(algoLabel).join('，')}`
  : '未选择')
const timeError = computed(() => draft.split_mode === 'time' && !draft.time_boundary ? '请选择训练与测试的时间边界' : '')
const thresholdError = computed(() => draft.threshold > 0 && draft.threshold < 1 ? '' : '判定阈值需在 0 到 1 之间')
const seedError = computed(() => draft.seed !== '' && Number.isInteger(Number(draft.seed)) && Number(draft.seed) >= 0 ? '' : '随机种子需为非负整数')
const canTrain = computed(() => {
  if (!hasInput.value || !selected.value.length) return false
  return !timeError.value && !thresholdError.value && !seedError.value
})
// 顶部步骤轨道：以输入、算法、划分三段就绪度推进，训练中与完成后收口到最后一步。
const railSteps = [
  { title: '选择输入', note: '清洗结果' },
  { title: '选择架构', note: '专家 / 语义' },
  { title: '选择算法', note: '算法组合' },
  { title: '划分数据', note: '划分方式' },
  { title: '运行', note: '开始训练' }
]
const activeStep = computed(() => {
  if (isRunning.value) return 4
  if (training.job?.status === 'success') return 4
  if (!hasInput.value) return 0
  if (!selected.value.length) return 2
  return 3
})
function stepState(index) {
  if (training.job?.status === 'success') return 'done'
  if (index < activeStep.value) return 'done'
  return index === activeStep.value ? 'current' : 'upcoming'
}
const registerText = computed(() => {
  const models = (result.value.models || []).filter(model => model.status === 'success')
  if (!models.length) return ''
  const registered = models.filter(model => String(model.register_status || '').startsWith('registered')).length
  const loaded = models.filter(model => String(model.load_status || '').startsWith('loaded')).length
  const failed = models.length - registered
  return `模型登记 ${registered}/${models.length}，已加载 ${loaded}${failed ? `，${failed} 个登记失败` : ''}`
})
watch(selected, list => {
  for (const algo of list) {
    if (draft.hyperparams[algo]) continue
    const item = algorithms.value.find(entry => entry.algo === algo)
    draft.hyperparams[algo] = Object.fromEntries(
      (item?.hyperparams_schema || []).map(param => [param.name, param.default])
    )
  }
})
function formatTime(value) {
  if (!value) return '未提供'
  return String(value).replace('T', ' ').replace(/\.\d+Z?$/, '').replace('Z', '').slice(0, 16)
}
function message(err) {
  if (err.code === 40100) { auth.value = true; return '登录已失效，请重新登录' }
  return err.code === 50000 ? '训练服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
async function loadAlgorithms() {
  algoLoading.value = true; selected.value = []; error.value = ''
  try {
    const data = await getAlgorithms({ line: line.value, enabled_only: 1 })
    algorithms.value = data.algorithms
    // 默认勾选后端标记为默认的算法，用户点一次即可开始训练。
    const preset = (data.algorithms || []).find(item => item.enabled)?.algo
    if (preset) selected.value = [preset]
  } catch (err) { error.value = message(err) }
  finally { algoLoading.value = false }
}
async function loadSources(page = 1) {
  sourcesLoading.value = true; sourcesError.value = ''
  try {
    const data = await loadArtifactJobs('clean', { page, size: 20 })
    Object.assign(sourceJobs, data)
    // 默认选中最近一次清洗产出的训练表，避免每次都手动挑选。
    if (!data.items.some(job => job.files.some(file => file.value === draft.source_id))) {
      const preferred = sources.value.find(file => !/report|stat|summary/i.test(file.name))
        || sources.value[0]
      draft.source_id = preferred?.value || ''
    }
  } catch (err) { sourcesError.value = message(err) }
  finally { sourcesLoading.value = false }
}
function snapshot() {
  const split = draft.split_mode === 'time'
    ? { time_boundary: `${draft.time_boundary}:00Z` }
    : { ratio: draft.ratio }
  return {
    line: line.value,
    feature_set: line.value === 'semantic' ? 'codebert768' : 'kamei14',
    algos: [...selected.value],
    hyperparams: Object.fromEntries(
      selected.value
        .filter(algo => draft.hyperparams[algo])
        .map(algo => [algo, { ...draft.hyperparams[algo] }])
    ),
    split,
    seed: Number(draft.seed),
    decision_threshold: Number(draft.threshold),
    // 模型统一由后端登记并热加载，页面不再提供保存方式选项
    register: true,
    auto_load: true
  }
}
function resetOutputs() {
  outputError.value = ''
}
async function submit() {
  if (busy.value || auth.value || isRunning.value || !canTrain.value) return
  busy.value = true; error.value = ''
  try {
    const config = snapshot()
    const uploads = await materializeArtifact(sourceJobs.items, draft.source_id, { extensions: ['.csv', '.xlsx'], includeCompanions: true })
    const accepted = await runTrain(config, uploads)
    if (!accepted?.job_id || !['queued', 'running', 'success', 'failed'].includes(accepted.status)) throw new Error('训练任务响应不完整')
    resetOutputs(); training.request = config; training.job = accepted
    scrollToResults()
    await refreshJob()
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
async function refreshJob() {
  if (!training.job?.job_id || refreshing.value || auth.value) return
  clearTimeout(timer); refreshing.value = true
  const id = training.job.job_id, token = ++jobEpoch
  try {
    const data = await getJob(id)
    if (!mounted || token !== jobEpoch || training.job?.job_id !== id) return
    if (data.kind !== 'train' || !['queued', 'running', 'success', 'failed', 'cancelled'].includes(data.status)) throw new Error('任务响应不完整')
    training.job = data
  } catch (err) { if (mounted && token === jobEpoch && training.job?.job_id === id) error.value = message(err) }
  finally {
    refreshing.value = false
    if (mounted && token === jobEpoch && ['queued', 'running'].includes(training.job?.status)) timer = setTimeout(refreshJob, 1500)
  }
}
async function retry() {
  try {
    const id = training.job.job_id
    await retryJob(id)
    resetOutputs(); training.job = await getJob(id)
    await refreshJob()
  } catch (err) { error.value = message(err) }
}
async function cancel() {
  try {
    const id = training.job.job_id
    await cancelJob(id)
    jobEpoch++; clearTimeout(timer)
    training.job = await getJob(id)
  } catch (err) { error.value = message(err) }
}
async function download(name) {
  downloading.value = true
  try { saveBlob(await fetchTrainOutput(training.job.job_id, name), name) }
  catch (err) { error.value = message(err) }
  finally { downloading.value = false }
}
onActivated(async () => {
  mounted = true; jobEpoch++
  // 二次进入保留数据集、算法与划分参数，只续接训练进度。
  if (activated) { await refreshJob(); return }
  activated = true
  await Promise.all([loadAlgorithms(), loadSources()])
  if (!training.job) {
    try { const data = await getJobs({ kind: 'train', size: 1 }); training.job = data.items?.[0] || null }
    catch (err) { error.value = message(err) }
  }
  if (training.request) {
    const request = training.request
    if (request.line) line.value = request.line
    if (Array.isArray(request.algos)) selected.value = [...request.algos]
    if (Number(request.decision_threshold) > 0) draft.threshold = Number(request.decision_threshold)
    if (Number(request.seed) >= 0) draft.seed = Number(request.seed)
    if (request.split?.time_boundary) {
      draft.split_mode = 'time'
      draft.time_boundary = String(request.split.time_boundary).slice(0, 16)
    } else if (Number(request.split?.ratio) > 0) {
      draft.ratio = Number(request.split.ratio)
    }
  }
  await refreshJob()
})
onDeactivated(() => { mounted = false; clearTimeout(timer) })
</script>

<style scoped>
/* 选项卡片与数据清洗页完全同款：check-list / is-active / check-note 由 ui.css 单源提供 */
.param-grid { margin: var(--ui-space-4) 0; }
.split-list { margin-bottom: var(--ui-space-3); }
@media (max-width: 768px) {
  .param-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>
