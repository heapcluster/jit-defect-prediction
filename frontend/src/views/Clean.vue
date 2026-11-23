<template>
  <section class="clean">
    <p class="hint">
      上传提交文件，先预览每一步的变化，再生成清洗文件。运行不写入提交或数据集展示表。
    </p>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <section
      class="panel"
      aria-labelledby="clean-input-title"
    >
      <h2 id="clean-input-title">
        输入文件
      </h2>
      <div class="fields">
        <label for="clean-files">提交主表及同名 manifest（CSV / XLSX + JSON）
          <input
            id="clean-files"
            type="file"
            multiple
            accept=".csv,.xlsx,.json"
            :disabled="busy || auth"
            @change="selectFiles"
          >
        </label>
        <label for="clean-dataset">已导入数据集（可选，上传文件优先）
          <select
            id="clean-dataset"
            v-model="draft.dataset_id"
            :disabled="busy || auth"
          ><option value="">不使用数据集，可直接上传</option><option
            v-for="item in datasets"
            :key="item.dataset_id"
            :value="item.dataset_id"
          >{{ item.name }}</option></select>
        </label>
      </div>
      <p
        v-if="files.length"
        class="file-note"
      >
        {{ files.map(file => file.name).join('；') }} <el-button
          size="small"
          :disabled="busy"
          @click="files = []"
        >
          移除文件
        </el-button>
      </p>
      <div class="fields">
        <label for="clean-source-artifact">收集产物库
          <select
            id="clean-source-artifact"
            v-model="selectedArtifact"
            :disabled="busy || auth"
          ><option value="">{{ sources.length ? '选择文件' : '暂无产物，可直接上传' }}</option><option
            v-for="source in sources"
            :key="source.value"
            :value="source.value"
          >{{ source.name }} · {{ source.job_id }}</option></select>
        </label>
        <div class="actions">
          <el-button
            data-testid="clean-use-artifact"
            :disabled="!selectedArtifact || busy || auth"
            @click="useArtifact"
          >
            使用文件与 manifest
          </el-button><el-button
            :disabled="busy || auth"
            @click="loadSources"
          >
            刷新来源
          </el-button>
        </div>
      </div>
      <p class="hint">
        输入为 Kamei v1 对数特征，清洗不会再次取对数。SZZ 步骤复核文件已有标签；没有回溯证据的记录保持未打标，不在本页重新运行 Git blame。
      </p>
    </section>
    <section
      class="panel"
      aria-labelledby="clean-chain-title"
    >
      <h2 id="clean-chain-title">
        处理链
      </h2>
      <el-skeleton
        v-if="loading"
        :rows="5"
        animated
      />
      <el-button
        v-if="!loading && !operations.length"
        @click="loadOperations"
      >
        重试加载操作注册表
      </el-button>
      <ol class="chain">
        <li
          v-for="(step, index) in steps"
          :key="step.op"
          data-testid="clean-step"
          :class="{ disabled: !step.enabled }"
          draggable="true"
          @dragstart="dragged = index"
          @dragover.prevent
          @drop.prevent="move(dragged, index)"
        >
          <div class="step-header">
            <label :for="`clean-enabled-${step.op}`"><input
              :id="`clean-enabled-${step.op}`"
              v-model="step.enabled"
              type="checkbox"
              :disabled="busy || auth"
            >{{ operation(step.op).name }}</label>
            <div class="step-actions">
              <el-button
                :data-testid="`clean-up-${step.op}`"
                size="small"
                :aria-label="`上移${operation(step.op).name}`"
                :disabled="index === 0 || busy || auth"
                @click="move(index, index - 1)"
              >
                上移
              </el-button><el-button
                size="small"
                :aria-label="`下移${operation(step.op).name}`"
                :disabled="index === steps.length - 1 || busy || auth"
                @click="move(index, index + 1)"
              >
                下移
              </el-button>
            </div>
          </div>
          <p class="hint">
            {{ operation(step.op).description }}
          </p>
          <details v-if="operation(step.op).params_schema?.length">
            <summary>操作参数</summary>
            <div class="fields parameters">
              <label
                v-for="param in operation(step.op).params_schema"
                :key="param.name"
                :for="`clean-param-${step.op}-${param.name}`"
              >{{ param.description || param.name }}
                <select
                  v-if="param.choices?.length"
                  :id="`clean-param-${step.op}-${param.name}`"
                  v-model="step.params[param.name]"
                  :disabled="busy || auth"
                ><option
                  v-for="choice in param.choices"
                  :key="String(choice)"
                  :value="choice"
                >{{ choice }}</option></select>
                <input
                  v-else-if="param.type === 'bool' || param.type === 'boolean'"
                  :id="`clean-param-${step.op}-${param.name}`"
                  v-model="step.params[param.name]"
                  type="checkbox"
                  :disabled="busy || auth"
                >
                <input
                  v-else
                  :id="`clean-param-${step.op}-${param.name}`"
                  v-model.number="step.params[param.name]"
                  :type="['float', 'int', 'number', 'integer'].includes(param.type) ? 'number' : 'text'"
                  :min="param.min"
                  :max="param.max"
                  :step="param.type === 'int' || param.type === 'integer' ? 1 : 'any'"
                  :disabled="busy || auth"
                >
              </label>
            </div>
          </details>
        </li>
      </ol>
      <p
        v-if="orderError"
        role="alert"
        class="validation"
      >
        {{ orderError }}
      </p>
      <fieldset class="feature-select">
        <legend>前后分布图特征（至少一项）</legend><label
          v-for="feature in featureChoices"
          :key="feature"
        ><input
          v-model="draft.features"
          data-testid="clean-feature"
          type="checkbox"
          :value="feature"
          :disabled="busy || auth"
        >{{ feature }}</label>
      </fieldset>
      <p
        v-if="!draft.features.length"
        class="validation"
      >
        至少选择一个图特征
      </p>
      <div class="fields">
        <label for="clean-mode">运行模式<select
          id="clean-mode"
          v-model="draft.mode"
          :disabled="busy || auth"
        ><option value="preview">预览 · 仅统计与分布图</option><option value="apply">应用 · 额外生成清洗文件</option></select></label>
        <label for="clean-seed">种子<input
          id="clean-seed"
          v-model.number="draft.seed"
          type="number"
          min="0"
          max="2147483647"
          step="1"
          :disabled="busy || auth"
        ></label>
        <label for="clean-format">优先下载格式<select
          id="clean-format"
          v-model="draft.format"
          :disabled="busy || auth"
        ><option value="csv">CSV（UTF-8 BOM）</option><option value="xlsx">XLSX（单 sheet）</option></select></label>
        <label for="clean-template">已保存模板<select
          id="clean-template"
          v-model="selectedTemplate"
          :disabled="busy || auth"
          @change="applyTemplate"
        ><option value="">选择模板</option><option
          v-for="name in Object.keys(templates)"
          :key="name"
          :value="name"
        >{{ name }}</option></select></label>
      </div>
      <div class="actions">
        <el-button
          data-testid="clean-run"
          type="primary"
          :loading="busy"
          :disabled="busy || auth || isRunning || !steps.length || !draft.features.length || Boolean(orderError)"
          @click="submit"
        >
          {{ draft.mode === 'preview' ? '预览清洗' : '生成清洗文件' }}
        </el-button><span class="hint">按时间序划分，不支持随机切分；标准化仅使用训练样本拟合。</span>
      </div>
      <div class="fields">
        <label for="clean-template-name">模板名称<input
          id="clean-template-name"
          v-model="templateName"
          maxlength="128"
          :disabled="busy || auth"
        ></label><div class="actions">
          <el-button
            data-testid="clean-save-template"
            :disabled="busy || auth || !steps.length || Boolean(orderError)"
            @click="saveTemplate"
          >
            保存当前处理链
          </el-button><span role="status">{{ templateMessage }}</span>
        </div>
      </div>
    </section>
    <section
      v-if="cleaning.job"
      class="panel"
      aria-live="polite"
      data-testid="clean-job"
    >
      <div class="heading">
        <h2>清洗任务</h2><el-tag>{{ statusLabel }}</el-tag>
      </div>
      <p class="mono">
        {{ cleaning.job.job_id }}
      </p>
      <el-progress
        :percentage="percentage"
        :status="cleaning.job.status === 'success' ? 'success' : undefined"
      />
      <p class="hint">
        {{ cleaning.job.current_item || '等待执行' }} · {{ cleaning.job.done || 0 }} / {{ cleaning.job.total || 0 }} · 重试 {{ cleaning.job.retry_count || 0 }} 次
      </p>
      <el-alert
        v-if="cleaning.job.error_log"
        :title="cleaning.job.error_log"
        type="error"
        :closable="false"
      />
      <div class="actions">
        <el-button
          :disabled="auth || refreshing"
          @click="refreshJob"
        >
          刷新状态
        </el-button><el-button
          v-if="cleaning.job.status === 'failed'"
          data-testid="clean-retry"
          :disabled="auth || refreshing"
          @click="retry"
        >
          重试原任务
        </el-button><el-button
          v-if="isRunning"
          data-testid="clean-cancel"
          :disabled="auth"
          @click="cancel"
        >
          取消任务
        </el-button>
      </div>
    </section>
    <section
      v-if="cleaning.job?.status === 'success'"
      class="panel"
      aria-labelledby="clean-result-title"
    >
      <h2 id="clean-result-title">
        {{ result.mode === 'apply' ? '清洗文件与处理记录' : '清洗预览 · 未生成主表' }}
      </h2>
      <p class="hint">
        输入 {{ result.summary?.input_rows }} 条 → {{ result.summary?.output_rows }} 条{{ result.mode === 'preview' ? '（模拟结果）' : '' }}
      </p>
      <p
        v-for="warning in result.summary?.warnings || []"
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
      <div class="table-scroll">
        <table>
          <thead><tr><th>操作</th><th>之前</th><th>之后</th><th>删除</th><th>修改</th><th>正 / 负 / 未打标</th><th>耗时 ms</th></tr></thead><tbody>
            <tr
              v-for="(step, index) in stats"
              :key="`${step.op}-${index}`"
            >
              <td>{{ operation(step.op).name || step.op }}</td><td>{{ step.rows_before }}</td><td>{{ step.rows_after }}</td><td>{{ step.removed }}</td><td>{{ step.modified }}</td><td>{{ labelDistribution(step.label_dist) }}</td><td>{{ step.elapsed_ms.toFixed(3) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <details
        v-for="(step, index) in stats.filter(item => item.excluded_samples?.length || item.modified_samples?.length)"
        :key="`samples-${index}`"
      >
        <summary>{{ operation(step.op).name || step.op }} · 样本明细</summary><ul class="sample-list">
          <li
            v-for="(sample, sampleIndex) in [...(step.excluded_samples || []), ...(step.modified_samples || [])]"
            :key="sampleIndex"
          >
            <code>{{ sample.commit_hash }}</code> · {{ sample.reason || JSON.stringify(sample) }}
          </li>
        </ul>
      </details>
      <div class="charts">
        <figure
          v-for="image in images"
          :key="image.name"
        >
          <img
            :src="image.url"
            :alt="`${image.name} 清洗前后分布`"
          ><figcaption>{{ image.name }}</figcaption>
        </figure>
      </div>
      <details v-if="featureStats">
        <summary>特征均值、中位数、标准差与分位数</summary><pre class="json-data">{{ JSON.stringify(featureStats, null, 2) }}</pre>
      </details>
      <div
        v-if="preview"
        data-testid="clean-preview"
      >
        <h3>清洗主表 · 前 20 行</h3><div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th
                  v-for="column in preview.columns"
                  :key="column"
                >
                  {{ column }}
                </th>
              </tr>
            </thead><tbody>
              <tr
                v-for="row in preview.preview"
                :key="row.commit_hash"
              >
                <td
                  v-for="column in preview.columns"
                  :key="column"
                >
                  {{ row[column] == null ? column === 'is_bug_inducing' ? '未打标' : '' : row[column] }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <h3>已登记文件</h3><ul class="output-list">
        <li
          v-for="item in result.outputs || []"
          :key="item.name"
        >
          <div><strong>{{ item.name }}</strong><span class="hint"> · {{ item.size_bytes }} bytes</span><code>{{ item.sha256 }}</code></div><el-button
            :data-testid="`clean-download-${item.name}`"
            size="small"
            :disabled="auth || downloading"
            @click="download(item.name)"
          >
            下载
          </el-button>
        </li>
      </ul>
      <div
        v-if="result.mode === 'apply'"
        class="import-block"
      >
        <h3>可选导入展示库</h3><p class="hint">
          仅显式导入才登记新数据集；原文件不覆盖。导入数据可能更新同提交的展示特征，已有预测冲突时后端拒绝。
        </p><div class="fields">
          <label for="clean-import-name">新数据集名称<input
            id="clean-import-name"
            v-model="importDraft.name"
          ></label><label for="clean-import-source">来源仓库<input
            id="clean-import-source"
            v-model="importDraft.repo_source"
          ></label>
        </div><el-button
          data-testid="clean-import"
          :disabled="auth || importing"
          :loading="importing"
          @click="importResult"
        >
          导入清洗文件
        </el-button><p role="status">
          {{ importMessage }}
        </p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { cancelJob, fetchCleanOutput, fetchCollectOutput, getCleanOperations, getCleanPreview, getDatasets, getJob, getJobs, importStorageFiles, putConfigKey, retryJob, runClean } from '../api'
import { cleaning } from '../utils/clean'
import { configuration, loadConfiguration } from '../utils/thresholds'

defineOptions({ name: 'CleanTool' })
const operations = ref([]), steps = ref([]), featureChoices = ref([]), loading = ref(false)
const draft = reactive({ dataset_id: '', mode: 'preview', features: [], seed: 42, split_ratio: 0.7, format: 'csv' })
const files = ref([]), datasets = ref([]), sources = ref([]), selectedArtifact = ref(''), selectedTemplate = ref(''), templateName = ref(''), templateMessage = ref('')
const busy = ref(false), auth = ref(false), error = ref(''), refreshing = ref(false), downloading = ref(false), importing = ref(false)
const stats = ref([]), featureStats = ref(null), images = ref([]), preview = ref(null), outputError = ref(''), importMessage = ref('')
const importDraft = reactive({ name: '', repo_source: '' })
let timer, mounted = true, outputJob = '', epoch = 0
let dragged = -1
const result = computed(() => cleaning.job?.output_ref_json || {})
const templates = computed(() => configuration.items.find(item => item.config_key === 'clean.chain_templates')?.value || {})
const isRunning = computed(() => ['queued', 'running'].includes(cleaning.job?.status))
const statusLabel = computed(() => ({ queued: '排队中', running: '运行中', success: '成功', failed: '失败', cancelled: '已取消' })[cleaning.job?.status] || '')
const percentage = computed(() => cleaning.job?.total ? Math.min(100, Math.floor(cleaning.job.done / cleaning.job.total * 100)) : 0)
const operation = op => operations.value.find(item => item.op === op) || {}
const orderError = computed(() => {
  const active = steps.value.filter(step => step.enabled), positions = Object.fromEntries(active.map((step, index) => [step.op, index]))
  for (const [index, step] of active.entries()) {
    for (const constraint of operation(step.op).order_constraints || []) {
      const other = positions[constraint.op]
      if ((constraint.type === 'first' && index !== 0) || (constraint.type === 'last' && index !== active.length - 1) ||
        (constraint.type === 'requires' && other === undefined) || (constraint.type === 'before' && other !== undefined && index >= other) ||
        (constraint.type === 'after' && other !== undefined && index <= other)) return `处理链顺序冲突：${operation(step.op).name} ${constraint.type} ${constraint.op || ''}`
    }
  }
  return ''
})
function message(err) {
  if (err.code === 40100) { auth.value = true; return '鉴权失败，请检查部署环境中的 API Key' }
  return err.code === 50000 ? '清洗服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
function selectFiles(event) { files.value = Array.from(event.target.files || []); event.target.value = '' }
function move(from, to) {
  if (busy.value || auth.value || from < 0 || to < 0 || from >= steps.value.length || to >= steps.value.length) return
  const [step] = steps.value.splice(from, 1); steps.value.splice(to, 0, step)
}
function snapshot() { return { mode: draft.mode, steps: JSON.parse(JSON.stringify(steps.value)), features: [...draft.features], seed: draft.seed, split_ratio: draft.split_ratio, format: draft.format } }
function labelDistribution(value) { return value ? `${value.positive ?? value['1'] ?? 0} / ${value.negative ?? value['0'] ?? 0} / ${value.unlabeled ?? value.null ?? 0}` : '' }
async function loadOperations() {
  loading.value = true
  try {
    const data = await getCleanOperations()
    if (!Array.isArray(data.operations) || !data.operations.length || !Array.isArray(data.features) || !data.features.length) throw new Error('操作注册表响应不完整')
    operations.value = data.operations; featureChoices.value = data.features; draft.features = [...data.features]
    steps.value = data.operations.map(item => restoreStep({ op: item.op, enabled: item.default_enabled !== false }))
  } catch (err) { error.value = message(err) }
  finally { loading.value = false }
}
async function loadSources() {
  try {
    const [jobs, data] = await Promise.all([getJobs({ kind: 'collect', status: 'success', size: 100 }), getDatasets({ size: 100, status: 'ready' })])
    sources.value = jobs.items.flatMap(job => (job.output_ref_json?.outputs || []).filter(item => item.name.endsWith('.csv') || item.name.endsWith('.xlsx')).map(item => ({ job_id: job.job_id, name: item.name, value: job.job_id + '/' + item.name })))
    datasets.value = data.items
  } catch (err) { error.value = message(err) }
}
async function useArtifact() {
  const source = sources.value.find(item => item.value === selectedArtifact.value)
  if (!source) return
  busy.value = true
  try {
    const manifest = source.name.replace(/\.[^.]+$/, '.manifest.json')
    const blobs = await Promise.all([fetchCollectOutput(source.job_id, source.name), fetchCollectOutput(source.job_id, manifest)])
    files.value = [new File([blobs[0]], source.name), new File([blobs[1]], manifest)]
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
function restoreStep(step, splitRatio) {
  const defaults = Object.fromEntries((operation(step.op).params_schema || []).map(param => [param.name, param.default]))
  if (step.op === 'time_split' && splitRatio !== undefined) defaults.ratio = splitRatio
  return { op: step.op, enabled: step.enabled ?? true, params: { ...defaults, ...step.params } }
}
function applyTemplate() {
  const template = templates.value[selectedTemplate.value]
  if (!template) return
  draft.split_ratio = template.split_ratio ?? 0.7
  steps.value = template.steps.map(step => restoreStep(step, draft.split_ratio))
  for (const field of ['features', 'seed', 'mode', 'format']) if (field in template) draft[field] = Array.isArray(template[field]) ? [...template[field]] : template[field]
}
async function saveTemplate() {
  if (!templateName.value.trim()) { templateMessage.value = '请填写模板名称'; return }
  busy.value = true
  try {
    await putConfigKey('clean.chain_templates', { ...templates.value, [templateName.value.trim()]: snapshot() })
    await loadConfiguration(); templateMessage.value = '处理链模板已保存，历史任务参数不变'
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
function resetOutputs() {
  epoch++; outputJob = ''; stats.value = []; featureStats.value = null; preview.value = null; outputError.value = ''
  for (const image of images.value) URL.revokeObjectURL(image.url)
  images.value = []
}
async function submit() {
  if (busy.value || auth.value || isRunning.value || orderError.value || !draft.features.length) return
  if (!files.value.length && !draft.dataset_id) { error.value = '请上传提交文件或选择数据集'; return }
  if (!Number.isInteger(draft.seed) || draft.seed < 0) { error.value = '种子必须为非负整数'; return }
  busy.value = true; error.value = ''; importMessage.value = ''
  try {
    const config = snapshot()
    if (draft.dataset_id && !files.value.length) config.dataset_id = draft.dataset_id
    const accepted = await runClean(config, files.value)
    if (!accepted?.job_id || !['queued', 'running', 'success', 'failed'].includes(accepted.status)) throw new Error('清洗任务响应不完整')
    resetOutputs(); cleaning.request = config; cleaning.job = accepted
    await refreshJob()
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
async function loadOutputs(id) {
  if (outputJob === id) return
  const ownEpoch = epoch, reference = result.value
  try {
    const statsName = reference.outputs.find(item => item.name.endsWith('.json') && item.name.startsWith('clean_steps_stats_')).name
    const featureName = reference.outputs.find(item => item.name.endsWith('.json') && item.name.startsWith('clean_feature_stats_')).name
    const [statsBlob, featureBlob] = await Promise.all([fetchCleanOutput(id, statsName), fetchCleanOutput(id, featureName)])
    const parsedStats = JSON.parse(await statsBlob.text()), parsedFeatures = JSON.parse(await featureBlob.text())
    const stagedImages = []
    for (const item of reference.outputs.filter(item => item.name.endsWith('.png'))) {
      const blob = await fetchCleanOutput(id, item.name)
      if (!mounted || ownEpoch !== epoch) return
      stagedImages.push({ name: item.name, blob })
    }
    const stagedPreview = reference.mode === 'apply' ? await getCleanPreview(id) : null
    if (!mounted || ownEpoch !== epoch || cleaning.job?.job_id !== id) return
    for (const image of images.value) URL.revokeObjectURL(image.url)
    images.value = stagedImages.map(image => ({ name: image.name, url: URL.createObjectURL(image.blob) }))
    stats.value = parsedStats; featureStats.value = parsedFeatures; preview.value = stagedPreview
    outputJob = id; outputError.value = ''
  } catch (err) { if (mounted && ownEpoch === epoch) outputError.value = message(err) }
}
async function refreshJob() {
  if (!cleaning.job?.job_id || refreshing.value || auth.value) return
  clearTimeout(timer); refreshing.value = true
  const id = cleaning.job.job_id
  try {
    const data = await getJob(id)
    if (!mounted || cleaning.job?.job_id !== id) return
    if (data.kind !== 'clean' || !['queued', 'running', 'success', 'failed', 'cancelled'].includes(data.status)) throw new Error('任务响应不完整')
    cleaning.job = data
    if (data.status === 'success') await loadOutputs(id)
    if (mounted && ['queued', 'running'].includes(data.status)) timer = setTimeout(refreshJob, 1500)
  } catch (err) { if (mounted && cleaning.job?.job_id === id) error.value = message(err) }
  finally {
    refreshing.value = false
    if (mounted && cleaning.job?.job_id !== id) refreshJob()
  }
}
async function retry() {
  try { const data = await retryJob(cleaning.job.job_id); resetOutputs(); cleaning.job = { ...cleaning.job, ...data }; await refreshJob() }
  catch (err) { error.value = message(err) }
}
async function cancel() {
  try { const data = await cancelJob(cleaning.job.job_id); cleaning.job = { ...cleaning.job, ...data }; clearTimeout(timer) }
  catch (err) { error.value = message(err) }
}
async function download(name) {
  downloading.value = true
  try {
    const blob = await fetchCleanOutput(cleaning.job.job_id, name), url = URL.createObjectURL(blob)
    try { const link = document.createElement('a'); link.href = url; link.download = name; link.click() }
    finally { URL.revokeObjectURL(url) }
  } catch (err) { error.value = message(err) }
  finally { downloading.value = false }
}
async function importResult() {
  if (!importDraft.name.trim() || !importDraft.repo_source.trim()) { importMessage.value = '请填写新数据集名称与来源仓库'; return }
  importing.value = true
  try {
    const name = result.value.outputs.find(item => item.name.endsWith('.csv')).name, manifest = name.replace(/\.csv$/, '.manifest.json')
    const blobs = await Promise.all([fetchCleanOutput(cleaning.job.job_id, name), fetchCleanOutput(cleaning.job.job_id, manifest)])
    const data = await importStorageFiles([new File([blobs[0]], name), new File([blobs[1]], manifest)], { create_dataset: { name: importDraft.name.trim(), repo_source: importDraft.repo_source.trim() } })
    if (!data?.items?.length || !data.summary) throw new Error('导入响应不完整')
    importMessage.value = data.summary.rejected || data.items.some(item => item.status === 'rejected') ? '存在拒绝项：' + data.items.flatMap(item => item.errors || []).join('；') : '清洗文件已导入，新数据集已登记'
  } catch (err) { importMessage.value = message(err) }
  finally { importing.value = false }
}
onMounted(async () => {
  await Promise.all([loadOperations(), loadSources()])
  if (!cleaning.job) {
    try { const data = await getJobs({ kind: 'clean', size: 1 }); cleaning.job = data.items?.[0] || null }
    catch (err) { error.value = message(err) }
  }
  await refreshJob()
})
onUnmounted(() => { mounted = false; clearTimeout(timer); resetOutputs() })
</script>

<style scoped>
.clean { min-width: 0; }
.panel { border: 1px solid var(--el-border-color-light); border-radius: var(--el-border-radius-base); padding: 18px; margin: 18px 0; }
h2 { margin: 0 0 16px; font-size: 16px; } h3 { font-size: 14px; margin: 20px 0 12px; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.65; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 16px 0; }
.fields label { display: flex; flex-direction: column; gap: 8px; font-size: 14px; min-width: 0; }
input:not([type="checkbox"]), select { box-sizing: border-box; width: 100%; min-width: 0; padding: 8px 10px; font: inherit; background: var(--el-fill-color-blank); color: var(--el-text-color-primary); border: 1px solid var(--el-border-color); border-radius: var(--el-border-radius-base); }
input:focus-visible, select:focus-visible, summary:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 2px; }
.actions, .heading { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.heading h2 { margin: 0; }
.chain { padding-left: 28px; }
.chain li { padding: 12px; border-bottom: 1px solid var(--el-border-color-lighter); }
.chain li::marker { font-family: ui-monospace, Menlo, monospace; color: var(--el-color-primary); }
.chain li.disabled { background: var(--el-fill-color-lighter); }
.step-header { display: flex; gap: 14px; align-items: center; justify-content: space-between; flex-wrap: wrap; }
.step-header label, .feature-select label { display: inline-flex; gap: 8px; align-items: center; font-size: 14px; }
.step-actions { display: flex; gap: 8px; }
.step-actions .el-button { margin-left: 0; }
.feature-select { border: 1px solid var(--el-border-color-light); display: flex; flex-wrap: wrap; gap: 14px; padding: 16px; }
.feature-select legend { font-size: 14px; }
summary { font-size: 13px; padding: 10px 0; cursor: pointer; }
.validation { font-size: 13px; color: var(--el-color-danger); overflow-wrap: anywhere; }
.file-note, .mono, code, .sample-list { font-size: 12px; overflow-wrap: anywhere; }
.mono, code, .json-data { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.table-scroll { overflow-x: auto; max-width: 100%; }
table { border-collapse: collapse; font-size: 12px; white-space: nowrap; font-variant-numeric: tabular-nums; }
th, td { border: 1px solid var(--el-border-color-light); padding: 10px; text-align: left; }
th { background: var(--el-fill-color-light); }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr)); gap: 18px; margin-top: 20px; }
figure { margin: 0; min-width: 0; } img { display: block; width: 100%; height: auto; } figcaption { font-size: 11px; color: var(--el-text-color-secondary); overflow-wrap: anywhere; }
.json-data { overflow: auto; max-height: 400px; font-size: 12px; }
.output-list { padding: 0; list-style: none; }
.output-list li { display: flex; gap: 14px; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.output-list li div { min-width: 0; overflow-wrap: anywhere; font-size: 12px; } .output-list code { display: block; margin-top: 5px; }
.import-block { border-top: 1px solid var(--el-border-color-light); margin-top: 20px; padding-top: 4px; }
@media (max-width: 640px) { .fields { grid-template-columns: minmax(0, 1fr); } .panel { padding: 14px; } .chain { padding-left: 20px; } .chain li { padding: 10px 0; } .step-header { align-items: flex-start; } .actions .el-button { margin-left: 0; } }
</style>
