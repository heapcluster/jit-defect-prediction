<template>
  <section class="evaluate">
    <p class="hint">
      上传 predictions（§3.4）、可选 labels（§3.5）与可选 effort 来源（§3.1 commits / §3.2 cleaned，按 la/ld 还原真实 LOC），按阈值与指标配置独立评估，交付指标长表、混淆矩阵、两类 effort 图与报告。不训练、不改概率；缺 effort 来源时 effort-aware 指标标注不可用。
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
      aria-labelledby="eval-input-title"
    >
      <h2 id="eval-input-title">
        输入与配置
      </h2>
      <label for="eval-files">predictions + 可选 labels + 可选 effort 来源 commits/cleaned（CSV/XLSX）
        <input
          id="eval-files"
          type="file"
          multiple
          accept=".csv,.xlsx"
          :disabled="busy || auth"
          @change="selectFiles"
        >
      </label>
      <p
        v-if="files.length"
        class="file-note"
      >
        {{ files.map(f => f.name).join('；') }} <el-button
          size="small"
          :disabled="busy"
          @click="files = []"
        >
          移除
        </el-button>
      </p>
      <div class="fields">
        <label for="eval-threshold">决策阈值（开区间 0–1）<input
          id="eval-threshold"
          v-model.number="draft.threshold"
          type="number"
          min="0.01"
          max="0.99"
          step="0.01"
          :disabled="busy || auth"
        ></label>
        <label for="eval-primary">主排序指标<select
          id="eval-primary"
          v-model="draft.primary"
          :disabled="busy || auth"
        ><option
          v-for="k in draft.metrics"
          :key="k"
          :value="k"
        >{{ k }}</option></select></label>
        <label for="eval-report">报告格式<select
          id="eval-report"
          v-model="draft.report"
          :disabled="busy || auth"
        ><option value="md">Markdown</option><option value="html">HTML</option></select></label>
      </div>
      <fieldset class="metric-select">
        <legend>指标（至少一项）</legend><label
          v-for="m in registry"
          :key="m.key"
        ><input
          v-model="draft.metrics"
          type="checkbox"
          :value="m.key"
          :disabled="busy || auth"
        >{{ m.key }} <span class="hint">· {{ m.name }}{{ m.effort_aware ? '（effort）' : '' }}</span></label>
      </fieldset>
      <label
        class="checkbox"
        for="eval-effort"
      ><input
        id="eval-effort"
        v-model="draft.effort"
        type="checkbox"
        :disabled="busy || auth"
      >启用 effort-aware 指标（需 LOC 工作量输入，缺省时披露不可用）</label>
      <div class="actions">
        <el-button
          data-testid="eval-run"
          type="primary"
          :loading="busy"
          :disabled="busy || auth || isRunning || !files.length || !draft.metrics.length"
          @click="submit"
        >
          运行评估
        </el-button><span class="hint">阈值只影响阈值相关指标，不改 AUC/AP 与 risk_score。</span>
      </div>
    </section>
    <section
      v-if="evaluating.job"
      class="panel"
      aria-live="polite"
      data-testid="eval-job"
    >
      <div class="heading">
        <h2>评估任务</h2><el-tag>{{ statusLabel }}</el-tag>
      </div>
      <p class="mono">
        {{ evaluating.job.job_id }}
      </p>
      <el-progress
        :percentage="percentage"
        :status="evaluating.job.status === 'success' ? 'success' : undefined"
      />
      <el-alert
        v-if="evaluating.job.error_log"
        :title="evaluating.job.error_log"
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
          v-if="evaluating.job.status === 'failed'"
          data-testid="eval-retry"
          :disabled="auth"
          @click="retry"
        >
          重试
        </el-button><el-button
          v-if="isRunning"
          data-testid="eval-cancel"
          :disabled="auth"
          @click="cancel"
        >
          取消
        </el-button>
      </div>
    </section>
    <section
      v-if="evaluating.job?.status === 'success'"
      class="panel"
      aria-labelledby="eval-result-title"
    >
      <h2 id="eval-result-title">
        评估结果
      </h2>
      <p class="hint">
        样本 {{ summary.rows }} · 主指标 {{ summary.primary_metric }} · 阈值 {{ summary.threshold }} · 标签统计 {{ JSON.stringify(summary.label_stats) }}
      </p>
      <el-alert
        v-if="outputError"
        :title="outputError"
        type="error"
        :closable="false"
      />
      <div class="table-scroll">
        <table data-testid="eval-comparison">
          <thead>
            <tr>
              <th>模型</th><th
                v-for="k in draft.metrics"
                :key="k"
              >
                {{ k }}
              </th><th>n</th><th>正样本率</th><th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="m in comparison"
              :key="m.model_name"
            >
              <td class="mono">
                {{ m.model_name }}
              </td><td
                v-for="k in draft.metrics"
                :key="k"
              >
                {{ fmt(m.metrics?.[k]) }}
              </td><td>{{ m.n }}</td><td>{{ fmt(m.pos_rate) }}</td><td>{{ m.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div
        v-if="unavailable.length"
        class="unavailable"
      >
        <h3>不可用原因</h3><ul>
          <li
            v-for="(u, i) in unavailable"
            :key="i"
          >
            {{ u.model_name || u.key }}：{{ u.reason_code }} — {{ u.message }}
          </li>
        </ul>
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
          <div><strong>{{ item.name }}</strong><code>{{ item.sha256 }}</code></div><el-button
            :data-testid="`eval-download-${item.name}`"
            size="small"
            :disabled="auth || downloading"
            @click="download(item.name)"
          >
            下载
          </el-button>
        </li>
      </ul>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { cancelJob, fetchEvaluateOutput, getEvaluateMetrics, getJob, getJobs, retryJob, runEvaluate } from '../api'
import { evaluating } from '../utils/evaluate'
import { configuration } from '../utils/thresholds'

defineOptions({ name: 'EvaluateTool' })
const registry = ref([]), files = ref([]), busy = ref(false), auth = ref(false), error = ref(''), refreshing = ref(false), downloading = ref(false)
const draft = reactive({ threshold: 0.5, metrics: [], primary: 'auc', effort: true, report: 'md' })
const comparison = ref([]), unavailable = ref([]), images = ref([]), outputError = ref('')
const summary = reactive({})
let timer, mounted = true, outputJob = '', epoch = 0
const result = computed(() => evaluating.job?.output_ref_json || {})
const isRunning = computed(() => ['queued', 'running'].includes(evaluating.job?.status))
const statusLabel = computed(() => ({ queued: '排队中', running: '运行中', success: '成功', failed: '失败', cancelled: '已取消' })[evaluating.job?.status] || '')
const percentage = computed(() => evaluating.job?.total ? Math.min(100, Math.floor(evaluating.job.done / evaluating.job.total * 100)) : 0)
const fmt = v => v == null ? '—' : Number(v).toFixed(4)
function message(err) {
  if (err.code === 40100) { auth.value = true; return '鉴权失败，请检查部署环境中的 API Key' }
  return err.code === 50000 ? '评估服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
function selectFiles(event) { files.value = Array.from(event.target.files || []); event.target.value = '' }
async function loadRegistry() {
  try {
    const data = await getEvaluateMetrics()
    registry.value = data.metrics
    draft.metrics = [...(data.defaults.metrics_selected || ['auc', 'ap', 'f1', 'precision', 'recall', 'accuracy'])]
    draft.primary = data.defaults.primary_metric || 'auc'
    draft.effort = data.defaults.effort_enabled ?? true
    draft.threshold = configuration.items.find(i => i.config_key === 'decision_threshold')?.value ?? 0.5
  } catch (err) { error.value = message(err) }
}
function resetOutputs() { epoch++; outputJob = ''; comparison.value = []; unavailable.value = []; outputError.value = ''; Object.keys(summary).forEach(k => delete summary[k]); for (const img of images.value) URL.revokeObjectURL(img.url); images.value = [] }
async function submit() {
  if (busy.value || auth.value || isRunning.value || !files.value.length || !draft.metrics.length) return
  if (!(draft.threshold > 0 && draft.threshold < 1)) { error.value = '阈值必须在开区间 (0,1)'; return }
  if (!draft.metrics.includes(draft.primary)) { error.value = '主排序指标必须属于已选指标'; return }
  busy.value = true; error.value = ''
  try {
    const config = { threshold: draft.threshold, metrics: [...draft.metrics], primary_metric: draft.primary, effort_enabled: draft.effort, report_format: draft.report }
    const accepted = await runEvaluate(config, files.value)
    if (!accepted?.job_id) throw new Error('评估任务响应不完整')
    resetOutputs(); evaluating.job = accepted
    await refreshJob()
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
async function loadOutputs(id) {
  if (outputJob === id) return
  const ownEpoch = epoch, reference = result.value
  try {
    const compName = (reference.outputs || []).find(i => i.name.startsWith('evaluate_comparison_')).name
    const compBlob = await fetchEvaluateOutput(id, compName)
    const comp = JSON.parse(await compBlob.text())
    const staged = []
    for (const item of (reference.outputs || []).filter(i => i.name.endsWith('.png'))) {
      const blob = await fetchEvaluateOutput(id, item.name)
      if (!mounted || ownEpoch !== epoch) return
      staged.push({ name: item.name, blob })
    }
    if (!mounted || ownEpoch !== epoch || evaluating.job?.job_id !== id) return
    for (const img of images.value) URL.revokeObjectURL(img.url)
    images.value = staged.map(i => ({ name: i.name, url: URL.createObjectURL(i.blob) }))
    comparison.value = comp.models || []; unavailable.value = comp.unavailable || []
    Object.assign(summary, reference.summary || {}); outputJob = id; outputError.value = ''
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
onMounted(async () => {
  await loadRegistry()
  if (!evaluating.job) { try { const data = await getJobs({ kind: 'evaluate', size: 1 }); evaluating.job = data.items?.[0] || null } catch (err) { error.value = message(err) } }
  await refreshJob()
})
onUnmounted(() => { mounted = false; clearTimeout(timer); resetOutputs() })
</script>

<style scoped>
.evaluate { min-width: 0; }
.panel { border: 1px solid var(--el-border-color-light); border-radius: var(--el-border-radius-base); padding: 18px; margin: 18px 0; }
h2 { margin: 0 0 16px; font-size: 16px; } h3 { font-size: 14px; margin: 16px 0 10px; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.6; }
.fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin: 16px 0; }
.fields label, .panel > label { display: flex; flex-direction: column; gap: 8px; font-size: 14px; min-width: 0; }
input:not([type="checkbox"]), select { box-sizing: border-box; width: 100%; min-width: 0; padding: 8px 10px; font: inherit; background: var(--el-fill-color-blank); color: var(--el-text-color-primary); border: 1px solid var(--el-border-color); border-radius: var(--el-border-radius-base); }
input:focus-visible, select:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 2px; }
.metric-select { border: 1px solid var(--el-border-color-light); display: flex; flex-wrap: wrap; gap: 12px; padding: 14px; margin: 12px 0; }
.metric-select label { display: inline-flex; gap: 6px; align-items: center; font-size: 13px; }
.checkbox { display: inline-flex; align-items: center; gap: 8px; font-size: 14px; margin: 10px 0; }
.actions, .heading { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; }
.heading h2 { margin: 0; }
.file-note, .mono, code { font-size: 12px; overflow-wrap: anywhere; }
.mono, code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.table-scroll { overflow-x: auto; max-width: 100%; }
table { border-collapse: collapse; font-size: 12px; white-space: nowrap; font-variant-numeric: tabular-nums; }
th, td { border: 1px solid var(--el-border-color-light); padding: 8px; text-align: left; }
th { background: var(--el-fill-color-light); }
.unavailable ul { font-size: 12px; color: var(--el-color-warning); }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr)); gap: 16px; margin-top: 18px; }
figure { margin: 0; min-width: 0; } img { display: block; width: 100%; height: auto; } figcaption { font-size: 11px; color: var(--el-text-color-secondary); overflow-wrap: anywhere; }
.output-list { padding: 0; list-style: none; }
.output-list li { display: flex; gap: 14px; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.output-list li div { min-width: 0; overflow-wrap: anywhere; font-size: 12px; } .output-list code { display: block; margin-top: 4px; }
@media (max-width: 640px) { .fields { grid-template-columns: minmax(0, 1fr); } .panel { padding: 14px; } }
</style>
