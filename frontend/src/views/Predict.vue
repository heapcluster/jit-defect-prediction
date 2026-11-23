<template>
  <section class="predict">
    <p class="hint">
      上传模型包与待预测特征文件，或选择已登记模型 / 已导入数据集。批量预测交付 predictions.csv，不写入展示库；导入为可选动作。模型加载/卸载/重载/设默认是独立管理操作。
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
      aria-labelledby="predict-models-title"
    >
      <h2 id="predict-models-title">
        模型管理
      </h2>
      <p class="hint">
        默认模型：{{ status.default_model || '—' }}<span v-if="status.fallback_reason"> · 回退原因：{{ status.fallback_reason }}</span>
      </p>
      <el-alert
        v-if="modelsError"
        :title="modelsError"
        type="error"
        :closable="false"
      />
      <div class="table-scroll">
        <table data-testid="predict-models">
          <thead><tr><th>模型</th><th>线</th><th>工件</th><th>运行时</th><th>版本</th><th>错误</th><th>操作</th></tr></thead>
          <tbody>
            <tr
              v-for="m in status.items || []"
              :key="m.model_name"
            >
              <td class="mono">
                {{ m.model_name }}
              </td><td>{{ m.line }}</td><td>{{ m.artifact_status }}</td><td>{{ m.runtime_state }}</td><td>{{ m.version_key }}</td><td>{{ m.load_error || '—' }}</td>
              <td class="ops">
                <el-button
                  :data-testid="`predict-load-${m.model_name}`"
                  size="small"
                  :disabled="auth || modelsBusy"
                  @click="modelAction(m.model_name, 'load')"
                >
                  加载
                </el-button><el-button
                  :data-testid="`predict-reload-${m.model_name}`"
                  size="small"
                  :disabled="auth || modelsBusy"
                  @click="modelAction(m.model_name, 'reload')"
                >
                  重载
                </el-button><el-button
                  :data-testid="`predict-unload-${m.model_name}`"
                  size="small"
                  :disabled="auth || modelsBusy"
                  @click="modelAction(m.model_name, 'unload')"
                >
                  卸载
                </el-button><el-button
                  size="small"
                  :disabled="auth || modelsBusy || m.artifact_status !== 'available'"
                  @click="setDefault(m.model_name)"
                >
                  设默认
                </el-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <el-button
        size="small"
        :disabled="auth || modelsBusy"
        @click="loadStatus"
      >
        刷新状态
      </el-button>
    </section>
    <section
      class="panel"
      aria-labelledby="predict-input-title"
    >
      <h2 id="predict-input-title">
        批量预测输入
      </h2>
      <div class="fields">
        <label for="predict-files">模型包 + 待预测文件（model_package.zip + 特征表 CSV/XLSX；e2e 可另传 commit_hash,text 文本表）
          <input
            id="predict-files"
            type="file"
            multiple
            accept=".zip,.csv,.xlsx"
            :disabled="busy || auth"
            @change="selectFiles"
          >
        </label>
        <p class="hint span-all">
          expert 用特征表；semantic/fused 用特征表提供哈希与 Kamei 特征，语义向量按哈希取预计算或在线编码（缺编码器时该行明确失败）；e2e 用已登记 codebert_e2e 模型，接收特征表或 commit_hash,text 文本表，不接受上传模型包。
        </p>
        <label for="predict-registered">已登记模型（便利，未上传模型包时使用）
          <select
            id="predict-registered"
            v-model="draft.model_name"
            :disabled="busy || auth"
          ><option value="">选择已登记模型</option><option
            v-for="name in registered"
            :key="name"
            :value="name"
          >{{ name }}</option></select>
        </label>
        <label for="predict-dataset">已导入数据集（便利，上传文件优先）
          <select
            id="predict-dataset"
            v-model="draft.dataset_id"
            :disabled="busy || auth"
          ><option value="">不使用数据集</option><option
            v-for="d in datasets"
            :key="d.dataset_id"
            :value="d.dataset_id"
          >{{ d.name }}</option></select>
        </label>
        <label for="predict-threshold">决策阈值（开区间 0–1）<input
          id="predict-threshold"
          v-model.number="draft.threshold"
          type="number"
          min="0.01"
          max="0.99"
          step="0.01"
          :disabled="busy || auth"
        ></label>
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
        <label for="predict-model-artifact">train 模型包产物库
          <select
            id="predict-model-artifact"
            v-model="modelArtifact"
            :disabled="busy || auth"
          ><option value="">{{ modelSources.length ? '选择模型包' : '暂无产物，可直接上传' }}</option><option
            v-for="s in modelSources"
            :key="s.value"
            :value="s.value"
          >{{ s.name }}</option></select>
        </label>
        <label for="predict-table-artifact">collect/clean 特征文件产物库
          <select
            id="predict-table-artifact"
            v-model="tableArtifact"
            :disabled="busy || auth"
          ><option value="">{{ tableSources.length ? '选择特征文件' : '暂无产物，可直接上传' }}</option><option
            v-for="s in tableSources"
            :key="s.value"
            :value="s.value"
          >{{ s.name }}</option></select>
        </label>
      </div>
      <div class="actions">
        <el-button
          :disabled="!modelArtifact || busy || auth"
          @click="useArtifact(modelArtifact, 'train')"
        >
          使用模型包
        </el-button><el-button
          :disabled="!tableArtifact || busy || auth"
          @click="useArtifact(tableArtifact, 'table')"
        >
          使用特征文件
        </el-button><el-button
          :disabled="busy || auth"
          @click="loadSources"
        >
          刷新来源
        </el-button>
      </div>
      <label
        class="checkbox"
        for="predict-force"
      ><input
        id="predict-force"
        v-model="draft.force"
        type="checkbox"
        :disabled="busy || auth"
      >force_recompute（忽略库中已有结果，全部重算）</label>
      <div class="actions">
        <el-button
          data-testid="predict-run"
          type="primary"
          :loading="busy"
          :disabled="busy || auth || isRunning || !canRun"
          @click="submit"
        >
          运行预测
        </el-button><span class="hint">阈值只影响 predicted_label，不改 risk_score；缺预测行与未打标留空，不填 0。</span>
      </div>
    </section>
    <section
      v-if="predicting.job"
      class="panel"
      aria-live="polite"
      data-testid="predict-job"
    >
      <div class="heading">
        <h2>预测任务</h2><el-tag>{{ statusLabel }}</el-tag>
      </div>
      <p class="mono">
        {{ predicting.job.job_id }}
      </p>
      <el-progress
        :percentage="percentage"
        :status="predicting.job.status === 'success' ? 'success' : undefined"
      />
      <p class="hint">
        {{ predicting.job.current_item || '等待执行' }} · {{ predicting.job.done || 0 }} / {{ predicting.job.total || 0 }} · 重试 {{ predicting.job.retry_count || 0 }} 次
      </p>
      <el-alert
        v-if="predicting.job.error_log"
        :title="predicting.job.error_log"
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
          v-if="predicting.job.status === 'failed'"
          data-testid="predict-retry"
          :disabled="auth || refreshing"
          @click="retry"
        >
          重试原任务
        </el-button><el-button
          v-if="isRunning"
          data-testid="predict-cancel"
          :disabled="auth"
          @click="cancel"
        >
          取消任务
        </el-button>
      </div>
    </section>
    <section
      v-if="predicting.job?.status === 'success'"
      class="panel"
      aria-labelledby="predict-result-title"
    >
      <h2 id="predict-result-title">
        预测结果
      </h2>
      <p class="hint">
        输入 {{ summary.input_rows }} · 成功 {{ summary.success_count }} · 失败 {{ summary.failed_count }} · 模型 {{ summary.model_name }} · 阈值 {{ summary.decision_threshold }}
      </p>
      <el-alert
        v-if="outputError"
        :title="outputError"
        type="error"
        :closable="false"
      />
      <div
        v-if="preview"
        data-testid="predict-preview"
        class="table-scroll"
      >
        <table>
          <thead>
            <tr>
              <th
                v-for="c in preview.columns"
                :key="c"
              >
                {{ c }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in preview.rows"
              :key="row.commit_hash"
            >
              <td
                v-for="c in preview.columns"
                :key="c"
                :class="{ mono: c === 'commit_hash' }"
              >
                {{ c === 'is_bug_inducing' && (row[c] == null || row[c] === '') ? '未打标' : row[c] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <h3>已登记文件</h3>
      <ul class="output-list">
        <li
          v-for="item in result.outputs || []"
          :key="item.name"
        >
          <div><strong>{{ item.name }}</strong><span class="hint"> · {{ item.size_bytes }} bytes</span><code>{{ item.sha256 }}</code></div><el-button
            :data-testid="`predict-download-${item.name}`"
            size="small"
            :disabled="auth || downloading"
            @click="download(item.name)"
          >
            下载
          </el-button>
        </li>
      </ul>
      <div class="import-block">
        <h3>可选导入展示库</h3><p class="hint">
          导入后按 (commit_hash, model_name) 幂等 upsert，风险列表 / 提交详情页可见；重复导入不产生重复记录。
        </p><el-button
          data-testid="predict-import"
          :disabled="auth || importing"
          :loading="importing"
          @click="importResult"
        >
          导入预测结果
        </el-button><p role="status">
          {{ importMessage }}
        </p>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { cancelJob, fetchPredictOutput, fetchTrainOutput, fetchCollectOutput, fetchCleanOutput, getDatasets, getJob, getJobs, getModels, getModelsStatus, importStorageFiles, loadModel, reloadModel, retryJob, runPredict, setDefaultModel, unloadModel } from '../api'
import { predicting } from '../utils/predict'
import { configuration } from '../utils/thresholds'

defineOptions({ name: 'PredictTool' })
const status = reactive({ default_model: '', fallback_reason: null, items: [] })
const modelsError = ref(''), modelsBusy = ref(false), registered = ref([]), datasets = ref([])
const modelSources = ref([]), tableSources = ref([]), modelArtifact = ref(''), tableArtifact = ref('')
const draft = reactive({ model_name: '', dataset_id: '', threshold: 0.5, force: false })
const files = ref([]), busy = ref(false), auth = ref(false), error = ref(''), refreshing = ref(false), downloading = ref(false), importing = ref(false)
const summary = reactive({}), preview = ref(null), outputError = ref(''), importMessage = ref('')
let timer, mounted = true, outputJob = '', epoch = 0
const result = computed(() => predicting.job?.output_ref_json || {})
const isRunning = computed(() => ['queued', 'running'].includes(predicting.job?.status))
const statusLabel = computed(() => ({ queued: '排队中', running: '运行中', success: '成功', failed: '失败', cancelled: '已取消' })[predicting.job?.status] || '')
const percentage = computed(() => predicting.job?.total ? Math.min(100, Math.floor(predicting.job.done / predicting.job.total * 100)) : 0)
const hasZip = computed(() => files.value.some(f => f.name.endsWith('.zip')))
const hasTable = computed(() => files.value.some(f => /\.(csv|xlsx)$/i.test(f.name)))
const canRun = computed(() => (hasZip.value || draft.model_name) && (hasTable.value || draft.dataset_id))
function message(err) {
  if (err.code === 40100) { auth.value = true; return '鉴权失败，请检查部署环境中的 API Key' }
  return err.code === 50000 ? '预测服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
function selectFiles(event) { files.value = Array.from(event.target.files || []); event.target.value = '' }
async function loadStatus() {
  modelsBusy.value = true
  try { Object.assign(status, await getModelsStatus()); modelsError.value = '' }
  catch (err) { modelsError.value = message(err) }
  finally { modelsBusy.value = false }
}
async function modelAction(name, action) {
  modelsBusy.value = true
  try {
    const fn = { load: loadModel, unload: unloadModel, reload: reloadModel }[action]
    await fn(name); await loadStatus()
  } catch (err) { modelsError.value = message(err) }
  finally { modelsBusy.value = false }
}
async function setDefault(name) {
  modelsBusy.value = true
  try { await setDefaultModel(name); await loadStatus() }
  catch (err) { modelsError.value = message(err) }
  finally { modelsBusy.value = false }
}
async function loadSources() {
  try {
    const [train, collect, clean, data, models] = await Promise.all([
      getJobs({ kind: 'train', status: 'success', size: 100 }), getJobs({ kind: 'collect', status: 'success', size: 100 }),
      getJobs({ kind: 'clean', status: 'success', size: 100 }), getDatasets({ size: 100, status: 'ready' }), getModels()])
    modelSources.value = train.items.flatMap(j => (j.output_ref_json?.outputs || []).filter(i => i.name.endsWith('.zip')).map(i => ({ job_id: j.job_id, name: i.name, value: j.job_id + '/' + i.name })))
    tableSources.value = [...collect.items, ...clean.items].flatMap(j => (j.output_ref_json?.outputs || []).filter(i => /\.(csv|xlsx)$/i.test(i.name)).map(i => ({ job_id: j.job_id, kind: j.kind, name: i.name, value: j.kind + '/' + j.job_id + '/' + i.name })))
    datasets.value = data.items
    registered.value = (models.lines || []).flatMap(l => l.models)
  } catch (err) { error.value = message(err) }
}
async function useArtifact(value, kind) {
  busy.value = true
  try {
    if (kind === 'train') {
      const [jobId, name] = value.split('/')
      const blob = await fetchTrainOutput(jobId, name)
      files.value = [...files.value.filter(f => !f.name.endsWith('.zip')), new File([blob], name)]
    } else {
      const [sourceKind, jobId, name] = value.split('/')
      const fetcher = sourceKind === 'clean' ? fetchCleanOutput : fetchCollectOutput
      const blob = await fetcher(jobId, name)
      files.value = [...files.value.filter(f => !/\.(csv|xlsx)$/i.test(f.name)), new File([blob], name)]
    }
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
function resetOutputs() { epoch++; outputJob = ''; preview.value = null; outputError.value = ''; Object.keys(summary).forEach(k => delete summary[k]) }
async function submit() {
  if (busy.value || auth.value || isRunning.value || !canRun.value) return
  if (!(draft.threshold > 0 && draft.threshold < 1)) { error.value = '阈值必须在开区间 (0,1)'; return }
  busy.value = true; error.value = ''; importMessage.value = ''
  try {
    const config = { decision_threshold: draft.threshold, force_recompute: draft.force }
    if (draft.model_name && !hasZip.value) config.model_name = draft.model_name
    if (draft.dataset_id && !hasTable.value) config.dataset_id = draft.dataset_id
    const accepted = await runPredict(config, files.value)
    if (!accepted?.job_id || !['queued', 'running', 'success', 'failed'].includes(accepted.status)) throw new Error('预测任务响应不完整')
    resetOutputs(); predicting.request = config; predicting.job = accepted
    await refreshJob()
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
async function loadOutputs(id) {
  if (outputJob === id) return
  const ownEpoch = epoch, reference = result.value
  try {
    const summaryName = (reference.outputs || []).find(i => i.name.startsWith('predict_summary_')).name
    const csvName = (reference.outputs || []).find(i => i.name.endsWith('.csv')).name
    const [summaryBlob, csvBlob] = await Promise.all([fetchPredictOutput(id, summaryName), fetchPredictOutput(id, csvName)])
    const parsedSummary = JSON.parse(await summaryBlob.text())
    const text = await csvBlob.text()
    const lines = text.replace(/^/, '').split(/\r?\n/).filter(Boolean)
    const columns = lines[0].split(',')
    const rows = lines.slice(1, 21).map(line => Object.fromEntries(line.split(',').map((v, i) => [columns[i], v])))
    if (!mounted || ownEpoch !== epoch || predicting.job?.job_id !== id) return
    Object.assign(summary, parsedSummary); preview.value = { columns, rows }; outputJob = id; outputError.value = ''
  } catch (err) { if (mounted && ownEpoch === epoch) outputError.value = message(err) }
}
async function refreshJob() {
  if (!predicting.job?.job_id || refreshing.value || auth.value) return
  clearTimeout(timer); refreshing.value = true
  const id = predicting.job.job_id
  try {
    const data = await getJob(id)
    if (!mounted || predicting.job?.job_id !== id) return
    if (data.kind !== 'predict_batch' || !['queued', 'running', 'success', 'failed', 'cancelled'].includes(data.status)) throw new Error('任务响应不完整')
    predicting.job = data
    if (data.status === 'success') await loadOutputs(id)
  } catch (err) { if (mounted && predicting.job?.job_id === id) error.value = message(err) }
  finally {
    refreshing.value = false
    if (mounted) {
      if (predicting.job?.job_id !== id) refreshJob()
      else if (['queued', 'running'].includes(predicting.job?.status)) timer = setTimeout(refreshJob, 1500)
    }
  }
}
async function retry() {
  try { const data = await retryJob(predicting.job.job_id); resetOutputs(); predicting.job = { ...predicting.job, ...data }; await refreshJob() }
  catch (err) { error.value = message(err) }
}
async function cancel() {
  try { const data = await cancelJob(predicting.job.job_id); predicting.job = { ...predicting.job, ...data }; clearTimeout(timer) }
  catch (err) { error.value = message(err) }
}
async function download(name) {
  downloading.value = true
  try {
    const blob = await fetchPredictOutput(predicting.job.job_id, name), url = URL.createObjectURL(blob)
    try { const link = document.createElement('a'); link.href = url; link.download = name; link.click() }
    finally { URL.revokeObjectURL(url) }
  } catch (err) { error.value = message(err) }
  finally { downloading.value = false }
}
async function importResult() {
  importing.value = true; importMessage.value = ''
  try {
    const name = (result.value.outputs || []).find(i => i.name.endsWith('.csv')).name
    const blob = await fetchPredictOutput(predicting.job.job_id, name)
    const data = await importStorageFiles([new File([blob], name)])
    importMessage.value = data?.summary?.rejected ? '存在拒绝项：' + (data.items || []).flatMap(i => i.errors || []).join('；') : '预测结果已导入，风险列表 / 提交详情页可见'
  } catch (err) { importMessage.value = message(err) }
  finally { importing.value = false }
}
onMounted(async () => {
  draft.threshold = configuration.items.find(i => i.config_key === 'decision_threshold')?.value ?? 0.5
  await Promise.all([loadStatus(), loadSources()])
  if (!predicting.job) {
    try { const data = await getJobs({ kind: 'predict_batch', size: 1 }); predicting.job = data.items?.[0] || null }
    catch (err) { error.value = message(err) }
  }
  await refreshJob()
})
onUnmounted(() => { mounted = false; clearTimeout(timer); resetOutputs() })
</script>

<style scoped>
.predict { min-width: 0; }
.panel { border: 1px solid var(--el-border-color-light); border-radius: var(--el-border-radius-base); padding: 18px; margin: 18px 0; }
h2 { margin: 0 0 16px; font-size: 16px; } h3 { font-size: 14px; margin: 20px 0 12px; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.65; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 16px 0; }
.fields .span-all { grid-column: 1 / -1; margin: 0; }
.fields label { display: flex; flex-direction: column; gap: 8px; font-size: 14px; min-width: 0; }
input:not([type="checkbox"]), select { box-sizing: border-box; width: 100%; min-width: 0; padding: 8px 10px; font: inherit; background: var(--el-fill-color-blank); color: var(--el-text-color-primary); border: 1px solid var(--el-border-color); border-radius: var(--el-border-radius-base); }
input:focus-visible, select:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 2px; }
.actions, .heading { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.heading h2 { margin: 0; }
.checkbox { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; margin: 10px 0; }
.file-note, .mono, code { font-size: 12px; overflow-wrap: anywhere; }
.mono, code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.table-scroll { overflow-x: auto; max-width: 100%; }
table { border-collapse: collapse; font-size: 12px; white-space: nowrap; font-variant-numeric: tabular-nums; }
th, td { border: 1px solid var(--el-border-color-light); padding: 10px; text-align: left; }
th { background: var(--el-fill-color-light); }
.ops { display: flex; gap: 6px; }
.ops .el-button { margin-left: 0; }
.output-list { padding: 0; list-style: none; }
.output-list li { display: flex; gap: 14px; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.output-list li div { min-width: 0; overflow-wrap: anywhere; font-size: 12px; } .output-list code { display: block; margin-top: 5px; }
.import-block { border-top: 1px solid var(--el-border-color-light); margin-top: 20px; padding-top: 4px; }
@media (max-width: 640px) { .fields { grid-template-columns: minmax(0, 1fr); } .panel { padding: 14px; } .actions .el-button { margin-left: 0; } }
</style>
