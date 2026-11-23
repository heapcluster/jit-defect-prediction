<template>
  <section class="train">
    <p class="hint">
      上传清洗或提交表格，多选算法并按算法库元数据配置超参，时间序训练后比较多个模型。训练不写入展示库，登记与加载为可选动作。
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
      aria-labelledby="train-input-title"
    >
      <h2 id="train-input-title">
        输入文件
      </h2>
      <div class="fields">
        <label for="train-files">训练主表及同名 manifest（CSV / XLSX + JSON）
          <input
            id="train-files"
            type="file"
            multiple
            accept=".csv,.xlsx,.json"
            :disabled="busy || auth"
            @change="selectFiles"
          >
        </label>
        <label for="train-dataset">已导入数据集（可选，上传文件优先）
          <select
            id="train-dataset"
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
        {{ files.map(f => f.name).join('；') }} <el-button
          size="small"
          :disabled="busy"
          @click="files = []"
        >
          移除文件
        </el-button>
      </p>
      <div class="fields">
        <label for="train-source-artifact">清洗 / 收集产物库
          <select
            id="train-source-artifact"
            v-model="selectedArtifact"
            :disabled="busy || auth"
          ><option value="">{{ sources.length ? '选择文件' : '暂无产物，可直接上传' }}</option><option
            v-for="s in sources"
            :key="s.value"
            :value="s.value"
          >{{ s.name }} · {{ s.job_id }}</option></select>
        </label>
        <div class="actions">
          <el-button
            data-testid="train-use-artifact"
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
    </section>
    <section
      class="panel"
      aria-labelledby="train-config-title"
    >
      <h2 id="train-config-title">
        模型线与算法
      </h2>
      <div class="fields">
        <label for="train-line">模型线
          <select
            id="train-line"
            v-model="line"
            :disabled="busy || auth"
            @change="loadAlgorithms"
          ><option value="expert">expert · 专家特征</option><option value="semantic">semantic · 语义特征</option><option value="fused">fused · 融合特征</option><option value="e2e">e2e · 端到端文本</option></select>
        </label>
        <label for="train-template">已保存模板
          <select
            id="train-template"
            v-model="selectedTemplate"
            :disabled="busy || auth"
            @change="applyTemplate"
          ><option value="">选择模板</option><option
            v-for="name in Object.keys(templates)"
            :key="name"
            :value="name"
          >{{ name }}</option></select>
        </label>
      </div>
      <el-alert
        v-if="lineWarning"
        :title="lineWarning"
        type="warning"
        :closable="false"
        show-icon
      />
      <el-skeleton
        v-if="algoLoading"
        :rows="3"
        animated
      />
      <ul class="algo-list">
        <li
          v-for="item in algorithms"
          :key="item.algo"
          data-testid="train-algo"
          :class="{ off: !item.enabled }"
        >
          <label :for="`train-algo-${item.algo}`"><input
            :id="`train-algo-${item.algo}`"
            v-model="selected"
            type="checkbox"
            :value="item.algo"
            :disabled="busy || auth || !item.enabled || Boolean(lineWarning)"
          >{{ item.algo }} <span class="hint">· {{ item.family }}{{ item.enabled ? '' : '（默认不训）' }}</span></label>
          <p class="hint">
            {{ item.description }} · 输入：{{ item.input_requirements }}
          </p>
          <details v-if="selected.includes(item.algo) && item.hyperparams_schema?.length">
            <summary>超参数（元数据驱动）</summary>
            <div class="fields parameters">
              <label
                v-for="p in item.hyperparams_schema"
                :key="p.name"
                :for="`train-hp-${item.algo}-${p.name}`"
              >{{ p.description || p.name }}
                <select
                  v-if="p.choices?.length"
                  :id="`train-hp-${item.algo}-${p.name}`"
                  v-model="hyperparams[item.algo][p.name]"
                  :disabled="busy || auth"
                ><option
                  v-for="c in p.choices"
                  :key="String(c)"
                  :value="c"
                >{{ c }}</option></select>
                <input
                  v-else-if="p.type === 'bool' || p.type === 'boolean'"
                  :id="`train-hp-${item.algo}-${p.name}`"
                  v-model="hyperparams[item.algo][p.name]"
                  type="checkbox"
                  :disabled="busy || auth"
                >
                <input
                  v-else
                  :id="`train-hp-${item.algo}-${p.name}`"
                  v-model.number="hyperparams[item.algo][p.name]"
                  :type="['int', 'integer', 'float', 'number'].includes(p.type) ? 'number' : 'text'"
                  :min="p.min"
                  :max="p.max"
                  :step="['int', 'integer'].includes(p.type) ? 1 : 'any'"
                  :disabled="busy || auth"
                >
              </label>
            </div>
          </details>
        </li>
      </ul>
      <div class="fields">
        <label for="train-split-mode">划分方式（时间序，禁随机）
          <select
            id="train-split-mode"
            v-model="splitMode"
            :disabled="busy || auth"
          ><option value="ratio">按比例</option><option value="boundary">按时间边界</option></select>
        </label>
        <label
          v-if="splitMode === 'ratio'"
          for="train-ratio"
        >训练比例<input
          id="train-ratio"
          v-model.number="draft.ratio"
          type="number"
          min="0.01"
          max="0.99"
          step="0.01"
          :disabled="busy || auth"
        ></label>
        <label
          v-else
          for="train-boundary"
        >时间边界（UTC，训练 ≤ 边界 &lt; 测试）<input
          id="train-boundary"
          v-model="draft.boundary"
          placeholder="2026-01-01T00:00:00Z"
          :disabled="busy || auth"
        ></label>
        <label for="train-seed">种子<input
          id="train-seed"
          v-model.number="draft.seed"
          type="number"
          min="0"
          step="1"
          :disabled="busy || auth"
        ></label>
        <label for="train-threshold">训练摘要阈值<input
          id="train-threshold"
          v-model.number="draft.threshold"
          type="number"
          min="0.01"
          max="0.99"
          step="0.01"
          :disabled="busy || auth"
        ></label>
      </div>
      <div class="actions">
        <label
          class="checkbox"
          for="train-register"
        ><input
          id="train-register"
          v-model="draft.register"
          type="checkbox"
          :disabled="busy || auth"
        >成功后登记工件</label>
        <label
          class="checkbox"
          for="train-autoload"
        ><input
          id="train-autoload"
          v-model="draft.auto_load"
          type="checkbox"
          :disabled="busy || auth"
        >成功后热加载（仅 expert）</label>
      </div>
      <div class="actions">
        <el-button
          data-testid="train-run"
          type="primary"
          :loading="busy"
          :disabled="busy || auth || isRunning || !selected.length || Boolean(lineWarning)"
          @click="submit"
        >
          运行训练
        </el-button><span class="hint">单算法失败不影响其他算法；失败不覆盖旧工件。</span>
      </div>
      <div class="fields">
        <label for="train-template-name">模板名称<input
          id="train-template-name"
          v-model="templateName"
          maxlength="128"
          :disabled="busy || auth"
        ></label><div class="actions">
          <el-button
            data-testid="train-save-template"
            :disabled="busy || auth || !selected.length"
            @click="saveTemplate"
          >
            保存当前配置
          </el-button><span role="status">{{ templateMessage }}</span>
        </div>
      </div>
    </section>
    <section
      v-if="training.job"
      class="panel"
      aria-live="polite"
      data-testid="train-job"
    >
      <div class="heading">
        <h2>训练任务</h2><el-tag>{{ statusLabel }}</el-tag>
      </div>
      <p class="mono">
        {{ training.job.job_id }}
      </p>
      <el-progress
        :percentage="percentage"
        :status="training.job.status === 'success' ? 'success' : undefined"
      />
      <p class="hint">
        {{ training.job.current_item || '等待执行' }} · {{ training.job.done || 0 }} / {{ training.job.total || 0 }} · 重试 {{ training.job.retry_count || 0 }} 次
      </p>
      <el-alert
        v-if="training.job.error_log"
        :title="training.job.error_log"
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
          v-if="training.job.status === 'failed'"
          data-testid="train-retry"
          :disabled="auth || refreshing"
          @click="retry"
        >
          重试原任务
        </el-button><el-button
          v-if="isRunning"
          data-testid="train-cancel"
          :disabled="auth"
          @click="cancel"
        >
          取消任务
        </el-button>
      </div>
    </section>
    <section
      v-if="training.job?.status === 'success'"
      class="panel"
      aria-labelledby="train-result-title"
    >
      <h2 id="train-result-title">
        多模型比较
      </h2>
      <p class="hint">
        主排序指标：{{ compare?.primary_metric }} · 成功 {{ result.summary?.success_count }} / 失败 {{ result.summary?.failed_count }} · 训练 {{ result.summary?.train_rows }} / 测试 {{ result.summary?.test_rows }} 行
      </p>
      <el-alert
        v-if="outputError"
        :title="outputError"
        type="error"
        :closable="false"
      />
      <div class="table-scroll">
        <table data-testid="train-comparison">
          <thead><tr><th>模型</th><th>线</th><th>算法</th><th>超参摘要</th><th>特征版本</th><th>AUC</th><th>F1</th><th>精确</th><th>召回</th><th>准确</th><th>状态</th><th>登记/加载</th></tr></thead>
          <tbody>
            <tr
              v-for="m in compare?.models || []"
              :key="m.model_name"
            >
              <td class="mono">
                {{ m.model_name }}
              </td><td>{{ m.line || line }}</td><td>{{ m.algo }}</td><td class="mono">
                {{ JSON.stringify(m.hyperparams) }}
              </td><td>{{ m.feature_version }}</td><td>{{ fmt(m.metrics?.auc) }}</td><td>{{ fmt(m.metrics?.f1) }}</td><td>{{ fmt(m.metrics?.precision) }}</td><td>{{ fmt(m.metrics?.recall) }}</td><td>{{ fmt(m.metrics?.accuracy) }}</td><td>{{ m.status }}{{ m.error ? '：' + m.error : '' }}</td><td>{{ subStatus(m.model_name).register_status || '—' }} / {{ subStatus(m.model_name).load_status || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="charts">
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
      <h3>已登记文件</h3>
      <ul class="output-list">
        <li
          v-for="item in result.outputs || []"
          :key="item.name"
        >
          <div><strong>{{ item.name }}</strong><span class="hint"> · {{ item.size_bytes }} bytes</span><code>{{ item.sha256 }}</code></div><el-button
            :data-testid="`train-download-${item.name}`"
            size="small"
            :disabled="auth || downloading"
            @click="download(item.name)"
          >
            下载
          </el-button>
        </li>
      </ul>
      <div class="import-block">
        <h3>可选登记模型工件</h3><p class="hint">
          未勾选自动登记时，可手动导入成功算法的模型包；登记后预测/解释页「已登记模型」可见，无需重启。
        </p><el-button
          data-testid="train-import"
          :disabled="auth || importing || !successModels.length"
          :loading="importing"
          @click="importModels"
        >
          导入模型包
        </el-button><p role="status">
          {{ importMessage }}
        </p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { cancelJob, fetchTrainOutput, getAlgorithms, getDatasets, getJob, getJobs, getTrainCompare, importStorageFiles, putConfigKey, retryJob, runTrain } from '../api'
import { training } from '../utils/train'
import { configuration, loadConfiguration } from '../utils/thresholds'

defineOptions({ name: 'TrainTool' })
const line = ref('expert'), algorithms = ref([]), algoLoading = ref(false), selected = ref([]), hyperparams = reactive({})
const draft = reactive({ dataset_id: '', ratio: 0.7, boundary: '', seed: 42, threshold: 0.5, register: false, auto_load: false })
const splitMode = ref('ratio'), files = ref([]), datasets = ref([]), sources = ref([]), selectedArtifact = ref('')
const selectedTemplate = ref(''), templateName = ref(''), templateMessage = ref('')
const busy = ref(false), auth = ref(false), error = ref(''), refreshing = ref(false), downloading = ref(false), importing = ref(false)
const compare = ref(null), images = ref([]), outputError = ref(''), importMessage = ref('')
let timer, mounted = true, outputJob = '', epoch = 0
const result = computed(() => training.job?.output_ref_json || {})
const templates = computed(() => configuration.items.find(i => i.config_key === 'train.templates')?.value || {})
const isRunning = computed(() => ['queued', 'running'].includes(training.job?.status))
const statusLabel = computed(() => ({ queued: '排队中', running: '运行中', success: '成功', failed: '失败', cancelled: '已取消' })[training.job?.status] || '')
const percentage = computed(() => training.job?.total ? Math.min(100, Math.floor(training.job.done / training.job.total * 100)) : 0)
const lineWarning = computed(() => line.value === 'expert' ? '' : `当前上传契约仅提供 Kamei 表格；${line.value} 线需要${line.value === 'e2e' ? '提交文本数据集' : 'CodeBERT 嵌入向量'}，不满足输入要求，后端将前置拒绝。请选择 expert 线。`)
const successModels = computed(() => (result.value.models || []).filter(m => m.status === 'success'))
const fmt = v => v == null ? '—' : Number(v).toFixed(4)
const subStatus = name => (result.value.models || []).find(m => m.model_name === name) || {}
function message(err) {
  if (err.code === 40100) { auth.value = true; return '鉴权失败，请检查部署环境中的 API Key' }
  return err.code === 50000 ? '训练服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
function selectFiles(event) { files.value = Array.from(event.target.files || []); event.target.value = '' }
function configItem(key) { return configuration.items.find(i => i.config_key === key)?.value }
async function loadAlgorithms() {
  algoLoading.value = true; selected.value = []; error.value = ''
  try {
    const data = await getAlgorithms({ line: line.value })
    algorithms.value = data.algorithms
    for (const item of data.algorithms) {
      hyperparams[item.algo] = Object.fromEntries((item.hyperparams_schema || []).map(p => [p.name, p.default]))
    }
  } catch (err) { error.value = message(err) }
  finally { algoLoading.value = false }
}
async function loadSources() {
  try {
    const [cleanJobs, collectJobs, data] = await Promise.all([getJobs({ kind: 'clean', status: 'success', size: 100 }), getJobs({ kind: 'collect', status: 'success', size: 100 }), getDatasets({ size: 100, status: 'ready' })])
    sources.value = [...cleanJobs.items, ...collectJobs.items].flatMap(job => (job.output_ref_json?.outputs || []).filter(i => i.name.endsWith('.csv') || i.name.endsWith('.xlsx')).map(i => ({ job_id: job.job_id, kind: job.kind, name: i.name, value: job.kind + '/' + job.job_id + '/' + i.name })))
    datasets.value = data.items
  } catch (err) { error.value = message(err) }
}
async function useArtifact() {
  const source = sources.value.find(s => s.value === selectedArtifact.value)
  if (!source) return
  busy.value = true
  try {
    const manifest = source.name.replace(/\.[^.]+$/, '.manifest.json')
    const fetcher = source.kind === 'clean' ? (await import('../api')).fetchCleanOutput : (await import('../api')).fetchCollectOutput
    const tableBlob = await fetcher(source.job_id, source.name)
    const manifestBlob = await fetcher(source.job_id, manifest).catch(() => null)
    files.value = [new File([tableBlob], source.name)]
    if (manifestBlob) files.value.push(new File([manifestBlob], manifest))
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
function snapshot() {
  const hp = {}
  for (const algo of selected.value) hp[algo] = Object.fromEntries(Object.entries(hyperparams[algo] || {}).filter(([, v]) => v != null && v !== ''))
  return { line: line.value, algos: [...selected.value], hyperparams: hp,
    split: splitMode.value === 'ratio' ? { ratio: draft.ratio } : { time_boundary: draft.boundary },
    seed: draft.seed, decision_threshold: draft.threshold, register: draft.register, auto_load: draft.auto_load }
}
function applyTemplate() {
  const t = templates.value[selectedTemplate.value]
  if (!t) return
  line.value = t.line; loadAlgorithms().then(() => {
    selected.value = [...t.algos]
    for (const algo of t.algos) hyperparams[algo] = { ...hyperparams[algo], ...(t.hyperparams?.[algo] || {}) }
    draft.seed = t.seed ?? 42; draft.threshold = t.decision_threshold ?? 0.5
    draft.register = t.register ?? false; draft.auto_load = t.auto_load ?? false
    if (t.split?.time_boundary) { splitMode.value = 'boundary'; draft.boundary = t.split.time_boundary }
    else { splitMode.value = 'ratio'; draft.ratio = t.split?.ratio ?? 0.7 }
  })
}
async function saveTemplate() {
  if (!templateName.value.trim()) { templateMessage.value = '请填写模板名称'; return }
  busy.value = true
  try {
    await putConfigKey('train.templates', { ...templates.value, [templateName.value.trim()]: snapshot() })
    await loadConfiguration(); templateMessage.value = '训练模板已保存，历史任务参数不变'
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
function resetOutputs() {
  epoch++; outputJob = ''; compare.value = null; outputError.value = ''
  for (const img of images.value) URL.revokeObjectURL(img.url)
  images.value = []
}
async function submit() {
  if (busy.value || auth.value || isRunning.value || !selected.value.length || lineWarning.value) return
  if (!files.value.length && !draft.dataset_id) { error.value = '请上传训练文件或选择数据集'; return }
  if (!Number.isInteger(draft.seed) || draft.seed < 0) { error.value = '种子必须为非负整数'; return }
  busy.value = true; error.value = ''; importMessage.value = ''
  try {
    const config = snapshot()
    if (draft.dataset_id && !files.value.length) config.dataset_id = draft.dataset_id
    const accepted = await runTrain(config, files.value)
    if (!accepted?.job_id || !['queued', 'running', 'success', 'failed'].includes(accepted.status)) throw new Error('训练任务响应不完整')
    resetOutputs(); training.request = config; training.job = accepted
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
      const blob = await fetchTrainOutput(id, item.name)
      if (!mounted || ownEpoch !== epoch) return
      staged.push({ name: item.name, blob })
    }
    const data = await getTrainCompare(id)
    if (!mounted || ownEpoch !== epoch || training.job?.job_id !== id) return
    for (const img of images.value) URL.revokeObjectURL(img.url)
    images.value = staged.map(i => ({ name: i.name, url: URL.createObjectURL(i.blob) }))
    compare.value = data; outputJob = id; outputError.value = ''
  } catch (err) { if (mounted && ownEpoch === epoch) outputError.value = message(err) }
}
async function refreshJob() {
  if (!training.job?.job_id || refreshing.value || auth.value) return
  clearTimeout(timer); refreshing.value = true
  const id = training.job.job_id
  try {
    const data = await getJob(id)
    if (!mounted || training.job?.job_id !== id) return
    if (data.kind !== 'train' || !['queued', 'running', 'success', 'failed', 'cancelled'].includes(data.status)) throw new Error('任务响应不完整')
    training.job = data
    if (data.status === 'success') await loadOutputs(id)
  } catch (err) { if (mounted && training.job?.job_id === id) error.value = message(err) }
  finally {
    refreshing.value = false
    if (mounted) {
      if (training.job?.job_id !== id) refreshJob()
      else if (['queued', 'running'].includes(training.job?.status)) timer = setTimeout(refreshJob, 1500)
    }
  }
}
async function retry() {
  try { const data = await retryJob(training.job.job_id); resetOutputs(); training.job = { ...training.job, ...data }; await refreshJob() }
  catch (err) { error.value = message(err) }
}
async function cancel() {
  try { const data = await cancelJob(training.job.job_id); training.job = { ...training.job, ...data }; clearTimeout(timer) }
  catch (err) { error.value = message(err) }
}
async function download(name) {
  downloading.value = true
  try {
    const blob = await fetchTrainOutput(training.job.job_id, name), url = URL.createObjectURL(blob)
    try { const link = document.createElement('a'); link.href = url; link.download = name; link.click() }
    finally { URL.revokeObjectURL(url) }
  } catch (err) { error.value = message(err) }
  finally { downloading.value = false }
}
async function importModels() {
  importing.value = true; importMessage.value = ''
  try {
    const messages = []
    for (const m of successModels.value) {
      const name = `train_${m.algo}_model_package_${training.job.job_id}.zip`
      const blob = await fetchTrainOutput(training.job.job_id, name)
      const data = await importStorageFiles([new File([blob], name)])
      messages.push(data?.summary?.rejected ? `${m.algo} 存在拒绝项` : `${m.algo} 已登记`)
    }
    importMessage.value = messages.join('；') || '没有可登记的成功模型'
  } catch (err) { importMessage.value = message(err) }
  finally { importing.value = false }
}
onMounted(async () => {
  draft.threshold = configItem('decision_threshold') ?? 0.5
  await Promise.all([loadAlgorithms(), loadSources()])
  if (!training.job) {
    try { const data = await getJobs({ kind: 'train', size: 1 }); training.job = data.items?.[0] || null }
    catch (err) { error.value = message(err) }
  }
  await refreshJob()
})
onUnmounted(() => { mounted = false; clearTimeout(timer); resetOutputs() })
</script>

<style scoped>
.train { min-width: 0; }
.panel { border: 1px solid var(--el-border-color-light); border-radius: var(--el-border-radius-base); padding: 18px; margin: 18px 0; }
h2 { margin: 0 0 16px; font-size: 16px; } h3 { font-size: 14px; margin: 20px 0 12px; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.65; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 16px 0; }
.fields label { display: flex; flex-direction: column; gap: 8px; font-size: 14px; min-width: 0; }
input:not([type="checkbox"]), select { box-sizing: border-box; width: 100%; min-width: 0; padding: 8px 10px; font: inherit; background: var(--el-fill-color-blank); color: var(--el-text-color-primary); border: 1px solid var(--el-border-color); border-radius: var(--el-border-radius-base); }
input:focus-visible, select:focus-visible, summary:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 2px; }
.actions, .heading { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.heading h2 { margin: 0; }
.checkbox { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; }
.algo-list { list-style: none; padding: 0; }
.algo-list li { padding: 12px; border-bottom: 1px solid var(--el-border-color-lighter); }
.algo-list li.off { background: var(--el-fill-color-lighter); }
.algo-list label { display: inline-flex; gap: 8px; align-items: center; font-size: 14px; }
summary { font-size: 13px; padding: 10px 0; cursor: pointer; }
.file-note, .mono, code { font-size: 12px; overflow-wrap: anywhere; }
.mono, code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.table-scroll { overflow-x: auto; max-width: 100%; }
table { border-collapse: collapse; font-size: 12px; white-space: nowrap; font-variant-numeric: tabular-nums; }
th, td { border: 1px solid var(--el-border-color-light); padding: 10px; text-align: left; }
th { background: var(--el-fill-color-light); }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr)); gap: 18px; margin-top: 20px; }
figure { margin: 0; min-width: 0; } img { display: block; width: 100%; height: auto; } figcaption { font-size: 11px; color: var(--el-text-color-secondary); overflow-wrap: anywhere; }
.output-list { padding: 0; list-style: none; }
.output-list li { display: flex; gap: 14px; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.output-list li div { min-width: 0; overflow-wrap: anywhere; font-size: 12px; } .output-list code { display: block; margin-top: 5px; }
.import-block { border-top: 1px solid var(--el-border-color-light); margin-top: 20px; padding-top: 4px; }
@media (max-width: 640px) { .fields { grid-template-columns: minmax(0, 1fr); } .panel { padding: 14px; } .actions .el-button { margin-left: 0; } }
</style>
