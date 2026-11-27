<template>
  <div class="panel config-panel content-page">
    <div class="section-heading">
      <h2>提交详情</h2>
    </div>
    <div class="head">
      <el-button
        link
        @click="$router.back()"
      >
        ← 返回
      </el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="mb"
    >
      <el-button
        v-if="errorCode === 40400"
        size="small"
        text
        @click="$router.push('/')"
      >
        返回列表
      </el-button>
      <el-button
        v-else-if="errorCode === 50000"
        size="small"
        text
        @click="load"
      >
        重试
      </el-button>
    </el-alert>

    <el-skeleton
      v-if="loading"
      :rows="6"
      animated
      class="skeleton"
    />

    <template v-if="detail">
      <!-- 风险结论行：风险分 + 等级 + 模型名，右侧为 SZZ 真标签 -->
      <div class="hero">
        <span
          v-if="!isNotPredicted"
          class="big"
          :style="{ color: riskColor(detail.risk_score) }"
        >
          {{ `${(detail.risk_score * 100).toFixed(1)}%` }}
        </span>
        <RiskTag
          :score="detail.risk_score"
          effect="dark"
        />
        <el-tag
          v-if="detail.model_name"
          type="info"
          size="small"
        >
          {{ detail.model_name }}
        </el-tag>
        <span class="spacer" />
        <el-tag
          v-if="detail.is_bug_inducing === 1"
          type="danger"
          size="small"
        >
          已确认有缺陷
        </el-tag>
        <el-tag
          v-else-if="detail.is_bug_inducing === 0"
          type="success"
          size="small"
        >
          已确认无缺陷
        </el-tag>
        <el-tag
          v-else
          type="info"
          size="small"
        >
          尚未标注
        </el-tag>
      </div>

      <p
        v-if="batchNotice"
        class="batch-notice"
      >
        {{ batchNotice }}
      </p>

      <h3>预测详情</h3>
      <div class="meta">
        <div class="row">
          <span class="k">提交</span>
          <span class="v mono">{{ detail.commit_hash }}</span>
        </div>
        <div class="row">
          <span class="k">作者</span>
          <span class="v">{{ detail.author_name }}</span>
        </div>
        <div class="row">
          <span class="k">时间</span>
          <span class="v">{{ formatTime(detail.committed_at) }}</span>
        </div>
        <div class="row">
          <span class="k">预测时间</span>
          <span class="v">{{ formatTime(detail.predicted_at) }}</span>
        </div>
        <div class="row">
          <span class="k">判定结果</span>
          <span class="v">{{ detail.predicted_label == null ? '未提供' : detail.predicted_label === 1 ? '缺陷' : '非缺陷' }}</span>
        </div>
        <div class="row">
          <span class="k">判定阈值</span><span class="v">{{ detail.decision_threshold ?? '未提供' }}</span>
        </div>
        <div class="row">
          <span class="k">预测模型</span><span class="v">{{ detail.model_name || '未提供' }}</span>
        </div>
        <div
          v-if="detail.stale"
          class="row"
        >
          <span class="k">状态</span>
          <el-tag
            size="small"
            type="warning"
          >
            模型已更新，建议重新预测
          </el-tag>
        </div>
        <div class="row">
          <span class="k">信息</span>
          <span class="v msg">{{ detail.message }}</span>
        </div>
      </div>

      <!-- 预测结果解释 -->
      <template v-if="!isNotPredicted">
        <h3>预测结果解释</h3>
        <div class="opbar">
          <label for="detail-technique">解释方式</label>
          <select
            id="detail-technique"
            v-model="explainTechnique"
            :disabled="explaining || forbidden"
            @change="loadExplanation"
          >
            <option
              v-for="technique in explainTechniques"
              :key="technique.key"
              :value="technique.key"
            >
              {{ technique.name }}
            </option>
          </select>
          <el-button
            size="small"
            :loading="explaining"
            :disabled="forbidden"
            @click="loadExplanation"
          >
            刷新解释
          </el-button>
        </div>
        <p
          v-if="explainError || explainMessage"
          role="status"
          class="muted"
        >
          {{ explainError || explainMessage }}
        </p>
        <p
          v-if="detail.summary"
          class="risk-summary"
        >
          {{ detail.summary }}
        </p>
        <div
          v-if="explanation.length"
          class="expl"
        >
          <div
            v-for="e in explanation"
            :key="e.feature"
            class="e"
          >
            <el-tooltip
              :content="e.feature"
              placement="top"
            >
              <span class="f">{{ e.label || featureLabel(e.feature) }}</span>
            </el-tooltip>
            <div class="track">
              <i
                :class="e.direction"
                :style="{ width: barWidth(e.contribution) }"
              />
            </div>
            <span class="val">{{ signed(e.contribution) }}</span>
          </div>
        </div>
        <el-empty
          v-else
          :description="explanationHint"
        >
          <el-button
            size="small"
            :loading="explaining"
            :disabled="forbidden || !detail.model_name"
            @click="loadExplanation"
          >
            生成解释
          </el-button>
        </el-empty>
      </template>

      <!-- 缺陷定位及修复：行级定位、修复建议与历史修复参考 -->
      <h3>缺陷定位及修复</h3>
      <LocalizationPanel
        :commit-hash="detail.commit_hash"
        :model-name="detail.model_name"
        :prediction="detail.prediction"
      />
      <template v-if="localization">
        <el-alert
          v-if="localization.level === 'commit'"
          :title="localization.notice"
          type="info"
          :closable="false"
          show-icon
          class="loc-notice"
        />
        <!-- 行级定位：按逐行可疑度分档着色（后端启发式，不是训练出的行级概率） -->
        <div
          v-if="localization.level === 'line' && localization.files.length"
          class="lines"
        >
          <div
            v-for="f in localization.files"
            :key="f.path"
            class="file"
          >
            <div class="file-path mono">
              {{ f.path }}
            </div>
            <div
              v-if="f.reasons && f.reasons.length"
              class="file-meta"
            >
              <el-tag size="small">
                优先程度 {{ Math.round((f.score || 0) * 100) }}%
              </el-tag>
              <span class="muted">{{ f.reasons.join('，') }}</span>
            </div>
            <div
              v-for="l in f.added_lines"
              :key="`${f.path}:${l.number}`"
              class="line"
              :style="{ borderLeftColor: lineColor(l.score), background: riskTint(l.score) }"
            >
              <span class="line-no mono">{{ l.number }}</span>
              <span class="line-content">{{ l.content }}</span>
              <span
                v-if="l.score != null"
                class="line-score"
              >{{ Math.round(l.score * 100) }}%</span>
            </div>
          </div>
          <div class="loc-legend">
            <span><i class="dot high" />优先检查 ≥70%</span>
            <span><i class="dot mid" />建议检查 40–70%</span>
            <span><i class="dot low" />一般 &lt;40%</span>
          </div>
          <div
            v-if="localization.truncated"
            class="muted"
          >
            仅展示最值得优先检查的部分代码。
          </div>
        </div>
        <!-- 提交级特征归因（始终保留） -->
        <div
          v-if="localization.highlights.length"
          class="loc"
        >
          <div
            v-for="(h, i) in localization.highlights"
            :key="h.feature"
            class="e"
          >
            <span class="rank">{{ i + 1 }}</span>
            <el-tooltip
              :content="h.feature"
              placement="top"
            >
              <span class="f">{{ h.label || featureLabel(h.feature) }}</span>
            </el-tooltip>
            <div class="track">
              <i
                :class="h.direction"
                :style="{ width: locBarWidth(h.contribution) }"
              />
            </div>
            <span class="val">{{ signed(h.contribution) }}</span>
          </div>
        </div>
        <el-empty
          v-else
          description="该模型未提供特征归因"
        />
      </template>

      <el-empty
        v-if="!localization && !fixReferences"
        description="当前提交暂无定位与修复结果，可在上方运行定位。"
      />

      <h3>影响判断的主要因素</h3>
      <div
        v-for="group in featureGroups"
        :key="group.title"
        class="group"
      >
        <h3>{{ group.title }}</h3>
        <div class="feats">
          <el-tooltip
            v-for="f in group.fields"
            :key="f"
            :content="f"
            placement="top"
          >
            <div class="feat">
              <span class="k">{{ featureLabel(f) }}</span>
              <span class="v">{{ featureValue(features[f]) }}</span>
            </div>
          </el-tooltip>
        </div>
      </div>

      <!-- 修复建议与参考：可执行建议 + 同仓库历史修复提交 -->
      <template v-if="fixReferences">
        <h4 class="subsection-title">
          修复建议与参考
        </h4>
        <div
          v-if="fixReferences.suggestions && fixReferences.suggestions.length"
          class="suggestions"
        >
          <ol>
            <li
              v-for="(s, i) in fixReferences.suggestions"
              :key="i"
            >
              {{ s }}
            </li>
          </ol>
        </div>
        <div
          v-if="fixReferences.items.length"
          class="refs"
        >
          <div
            v-for="r in fixReferences.items"
            :key="r.commit_hash"
            class="ref"
          >
            <span class="mono ref-hash">{{ r.commit_hash.slice(0, 8) }}</span>
            <span class="ref-msg">{{ r.message }}</span>
            <span class="ref-time">{{ formatTime(r.committed_at) }}</span>
          </div>
        </div>
        <el-empty
          v-else
          description="暂无同类历史修复提交"
        />
      </template>

      <h3>重新预测</h3>
      <div class="opbar">
        <LineModelCascade
          v-model:line="predictLine"
          v-model:model="predictModel"
          :lines="lines"
          model-placeholder="选择模型"
        />
        <el-button
          size="small"
          type="primary"
          :loading="predicting"
          :disabled="forbidden || !predictModel"
          @click="predict"
        >
          预测
        </el-button>
        <label class="force-recompute"><input
          v-model="forceRecompute"
          type="checkbox"
          :disabled="forbidden"
        >立即重算</label>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchPredictOutput, getCommitDetail, getExplainTechniques, getJob, postExplain, postPredict } from '../api'
import { ElMessage } from 'element-plus'
import { riskColor } from '../utils/risk'
import { loadModelLines } from '../utils/models'
import { FEATURE_GROUPS, featureLabel } from '../utils/features'
import { errText } from '../utils/errors'
import { formatTime } from '../utils/datetime'
import { parseCsv } from '../utils/csv'
import LineModelCascade from '../components/LineModelCascade.vue'
import LocalizationPanel from '../components/LocalizationPanel.vue'
import RiskTag from '../components/RiskTag.vue'

const props = defineProps({
  hash: { type: String, required: true }
})

const route = useRoute()

const detail = ref(null)
const loading = ref(false)
const error = ref('')
const errorCode = ref(0)
const batchNotice = ref('')

// 重新预测：架构 → 模型级联
const lines = ref([])
const predictLine = ref('')
const predictModel = ref('')
const predicting = ref(false)
const forceRecompute = ref(false)
const forbidden = ref(false)
const explainTechniques = ref([]), explainTechnique = ref(''), explaining = ref(false)
const explainError = ref(''), explainMessage = ref(''), explainSpace = ref('')
let explainEpoch = 0

const featureGroups = FEATURE_GROUPS

const features = computed(() => detail.value?.features || {})
// 提交存在但无预测记录时 risk_score 为 null
const isNotPredicted = computed(() => detail.value?.risk_score == null)
const explanation = computed(() => {
  const list = detail.value?.explanation || []
  // 按 |contribution| 降序，只显示前 8 项
  return [...list]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, 8)
})

const explanationHint = computed(() => '当前模型暂不支持逐项解释，可换用支持解释的模型。')

const maxContribution = computed(() =>
  Math.max(...explanation.value.map((e) => Math.abs(e.contribution)), 0.000001)
)

function barWidth(contribution) {
  const pct = (Math.abs(contribution) / maxContribution.value) * 100
  return `${pct.toFixed(0)}%`
}

// 缺陷定位（G1-1）与修复参考（G1-2）：后端新增字段，缺省时隐藏对应区块
const localization = computed(() => detail.value?.localization || null)
const fixReferences = computed(() => detail.value?.fix_references || null)
const locMax = computed(() =>
  Math.max(
    ...(localization.value?.highlights || []).map((h) => Math.abs(h.contribution)),
    0.000001
  )
)

function locBarWidth(contribution) {
  const pct = (Math.abs(contribution) / locMax.value) * 100
  return `${pct.toFixed(0)}%`
}

// 行背景按逐行可疑度着色（服务端启发式：提交风险 × 文件/hunk 权重 × 行内容）
// 行级可疑度分档：≥70% 红、40–70% 橙、<40% 绿（与图例一致）
function lineColor(score) {
  const value = score || 0
  if (value >= 0.7) return 'var(--ui-danger)'
  if (value >= 0.4) return 'var(--ui-warning)'
  return 'var(--ui-success)'
}

function riskTint(score) {
  return `color-mix(in srgb, ${lineColor(score)} 10%, transparent)`
}

function signed(v) {
  return (v > 0 ? '+' : '') + v.toFixed(2)
}

// 特征值保留 4 位小数（log 变换值可负）
function featureValue(value) {
  if (value === null || value === undefined) return '—'
  const number = Number(value)
  if (Number.isNaN(number)) return String(value)
  return Number.isInteger(number) ? String(number) : number.toFixed(4)
}

// 从模型预测页进入时带批次任务号：批量结果不写库，预测详情直接读该批次的预测产物。
const jobId = computed(() => typeof route.query.job_id === 'string' ? route.query.job_id : '')

// 重新预测默认沿用本条预测的模型，避免用户再次手选。
function syncPredictModel() {
  const model = detail.value?.model_name
  if (!model) return
  predictModel.value = model
  const match = lines.value.find(item => (item.models || []).includes(model))
  if (match) predictLine.value = match.line
}

async function loadBatchPrediction(job) {
  const reference = job?.output_ref_json || {}
  const name = (reference.outputs || [])
    .find(item => item.name.includes('predictions') && item.name.endsWith('.csv'))?.name
  if (!name) return null
  const text = await (await fetchPredictOutput(job.job_id, name)).text()
  const parsed = parseCsv(text)
  if (!parsed.columns.includes('commit_hash')) return null
  const target = props.hash.toLowerCase()
  const row = parsed.rows.find(item => String(item.commit_hash).trim().toLowerCase() === target)
  if (!row) return null
  const risk = Number(row.risk_score)
  if (!Number.isFinite(risk)) return null
  const threshold = Number(row.decision_threshold)
  const label = row.is_bug_inducing
  return {
    commit_hash: props.hash,
    model_name: row.model_name,
    risk_score: risk,
    predicted_label: Number(row.predicted_label),
    decision_threshold: Number.isFinite(threshold) ? threshold : null,
    model_version: row.model_version,
    feature_version: row.feature_version,
    predicted_at: row.predicted_at,
    is_bug_inducing: label === '' || label == null ? null : Number(label),
    summary: `本批次预测：风险分 ${(risk * 100).toFixed(1)}%${
      Number.isFinite(threshold) ? `，判定阈值 ${threshold.toFixed(2)}` : ''
    }。`
  }
}

async function load() {
  loading.value = true
  error.value = ''
  errorCode.value = 0
  explainError.value = ''
  explainMessage.value = ''
  try {
    let batch = null, batchError = null
    if (jobId.value) {
      try { batch = await loadBatchPrediction(await getJob(jobId.value)) }
      catch (caught) { batchError = caught; batch = null }
    }
    // 后端详情接口强制要求 model_name：深链未带时先从批次结果、再从已登记模型解析。
    let model = typeof route.query.model_name === 'string' ? route.query.model_name : ''
    if (!model) model = batch?.model_name || ''
    if (!model) {
      const available = await loadModelLines()
      model = available.find(item => item.models?.length)?.models?.[0] || ''
    }
    let base = null, baseError = null
    try {
      base = await getCommitDetail(props.hash, model)
      // 后端把判定字段放在 prediction 里，页面统一读顶层。
      if (base?.prediction) base = { ...base, ...base.prediction }
    } catch (caught) {
      if (caught?.code === 40100) throw caught
      baseError = caught
    }
    if (!base && !batch) throw baseError || new Error('提交详情不可用')
    detail.value = batch
      ? {
        ...(base || { features: {}, explanation: [] }),
        ...batch,
        features: base?.features || {},
        is_bug_inducing: batch.is_bug_inducing ?? base?.is_bug_inducing ?? null
      }
      : base
    batchNotice.value = batchError
      ? '批次预测结果读取失败，当前仅显示库内详情，可刷新页面重试。'
      : batch && !base
        ? '该提交不在展示库中，以上为本批次预测结果；逐项解释需先生成单条预测。'
        : ''
    syncPredictModel()
    await loadExplanation()
  } catch (e) {
    detail.value = null
    errorCode.value = e?.code || 0
    error.value = errText(e)
  } finally {
    loading.value = false
  }
}

async function loadExplanation() {
  if (!detail.value?.model_name || detail.value.risk_score == null) return
  const epoch = ++explainEpoch, id = detail.value.commit_hash, model = detail.value.model_name
  explaining.value = true; explainError.value = ''; explainMessage.value = ''
  try {
    const metadata = await getExplainTechniques({ model_name: model })
    if (epoch !== explainEpoch) return
    explainTechniques.value = metadata.techniques
    if (!explainTechnique.value) explainTechnique.value = metadata.default_technique
    const response = await postExplain(id, model, explainTechnique.value, { top_n: 8 })
    if (epoch !== explainEpoch || detail.value?.model_name !== model) return
    detail.value.explanation = response.items
    explainMessage.value = response.message || response.reason_code || ''
    explainSpace.value = response.output_space || ''
  } catch (err) {
    if (epoch === explainEpoch && detail.value?.model_name === model) {
      detail.value.explanation = []
      explainError.value = err.code === 40400 && jobId.value
        ? '本批次结果尚未入库，逐项解释需先在下方「重新预测」生成单条结果。'
        : err.detail || err.message || '解释服务不可用'
    }
  } finally { if (epoch === explainEpoch) explaining.value = false }
}

async function predict() {
  if (!detail.value) return
  predicting.value = true
  try {
    const data = await postPredict(detail.value.commit_hash, predictModel.value || undefined, { force_recompute: forceRecompute.value })
    detail.value = {
      ...detail.value,
      risk_score: data.risk_score,
      model_name: data.model_name,
      predicted_at: data.predicted_at,
      explanation: [],
      summary: data.summary || null,
      features: data.features || detail.value.features,
      predicted_label: data.predicted_label,
      decision_threshold: data.decision_threshold,
      risk_level: data.risk_level,
      model_version: data.model_version,
      feature_version: data.feature_version,
      result_source: data.result_source,
      stale: data.stale
    }
    ElMessage.success('预测完成')
    await loadExplanation()
  } catch (e) {
    // 40100 令牌失效：不给重试，禁用预测按钮
    if (e?.code === 40100) forbidden.value = true
    ElMessage.error(errText(e))
  } finally {
    predicting.value = false
  }
}

onUnmounted(() => { explainEpoch++ })

onMounted(() => {
  load()
  loadModelLines().then((l) => {
    lines.value = l
    syncPredictModel()
  })
})
// 路由参数变化时重载：组件复用时不重载会显示上一条提交
watch(
  () => props.hash,
  () => {
    detail.value = null
    batchNotice.value = ''
    errorCode.value = 0
    load()
  }
)
</script>

<style scoped>
.head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.mb {
  margin-bottom: 12px;
}
.skeleton {
  min-height: 300px;
}
.hero {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin: 4px 0 14px;
}
.big {
  font-size: var(--ui-font-2xl);
  font-weight: 700;
  font-family: var(--ui-font-mono);
  letter-spacing: -0.03em;
  line-height: 1;
}
.spacer {
  flex: 1;
}
.muted {
  color: var(--ui-text-muted);
  font-size: var(--ui-font-hint);
  line-height: 1.6;
}
.batch-notice {
  margin: 0 0 12px;
  padding: 8px 12px;
  border-left: 3px solid var(--ui-primary);
  border-radius: var(--ui-radius-md);
  background: var(--ui-primary-soft);
  color: var(--ui-text);
  font-size: var(--ui-font-hint);
  line-height: 1.6;
}
.opbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.expl {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 8px 0 16px;
}
.risk-summary {
  margin: 8px 0 12px;
  padding: 10px 12px;
  border-left: 3px solid var(--el-color-primary);
  background: var(--ui-primary-soft);
  border-radius: var(--ui-radius-md);
  line-height: 1.6;
}
.file-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 2px 0 6px;
  font-size: var(--ui-font-hint);
}
.suggestions {
  margin: 8px 0 16px;
  padding: 10px 14px;
  background: var(--el-color-success-light-9);
  border-left: 3px solid var(--el-color-success);
  border-radius: var(--ui-radius-md);
}
.suggestions ol {
  margin: 0;
  padding-left: 20px;
  line-height: 1.8;
}
.e {
  display: flex;
  align-items: center;
  gap: 10px;
}
.e .f {
  width: 110px;
  font-size: var(--ui-font-sm);
}
.e .track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: var(--ui-color-slate-100);
  overflow: hidden;
}
.e .track i {
  display: block;
  height: 100%;
  border-radius: inherit;
}
.e .track i.increase {
  background: var(--ui-danger);
}
.e .track i.decrease {
  background: var(--ui-success);
}
.e .val {
  width: 68px;
  text-align: right;
  white-space: nowrap;
  font-family: var(--ui-font-mono);
  color: var(--ui-text-muted);
}
.loc-notice {
  margin: 0 0 10px;
}
.lines {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 8px 0 16px;
}
.file-path {
  font-size: var(--ui-font-hint);
  color: var(--ui-text-muted);
  margin-bottom: 4px;
  word-break: break-all;
}
.line {
  display: flex;
  gap: 10px;
  padding: 4px 10px;
  border-left: 3px solid transparent;
  border-radius: var(--ui-radius-sm);
  font-family: var(--ui-font-mono);
  font-size: var(--ui-font-hint);
  line-height: 1.65;
}
.line:hover {
  background: var(--ui-surface-subtle);
}
.line-no {
  min-width: 36px;
  text-align: right;
  color: var(--ui-text-muted);
  user-select: none;
}
.line-content {
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}
.line-score {
  min-width: 42px;
  text-align: right;
  color: var(--ui-text-muted);
  font-size: 11px;
}
.loc-legend {
  display: flex;
  gap: 16px;
  margin-top: 4px;
  color: var(--ui-text-muted);
  font-size: var(--ui-font-hint);
}
.loc-legend .dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 3px;
  margin-right: 5px;
}
.loc-legend .dot.high {
  background: var(--ui-danger);
}
.loc-legend .dot.mid {
  background: var(--ui-warning);
}
.loc-legend .dot.low {
  background: var(--ui-success);
}
.loc {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 8px 0 16px;
}
.loc .rank {
  width: 18px;
  font-size: var(--ui-font-hint);
  color: var(--ui-text-muted);
  text-align: center;
}
.refs {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 8px 0 16px;
}
.ref {
  display: flex;
  align-items: baseline;
  gap: 10px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  padding: 10px 14px;
  background: var(--ui-surface);
}
.ref-hash {
  color: var(--ui-text-muted);
  font-size: var(--ui-font-hint);
}
.ref-msg {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}
.ref-time {
  color: var(--ui-text-muted);
  font-size: var(--ui-font-hint);
  white-space: nowrap;
}
.meta {
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  overflow: hidden;
  margin: 0 0 20px;
}
.meta .row {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--ui-border);
}
.meta .row:last-child {
  border-bottom: none;
}
.meta .k {
  color: var(--ui-text-muted);
  font-size: var(--ui-font-sm);
}
.meta .v {
  min-width: 0;
  word-break: break-word;
}
.meta .msg {
  white-space: pre-wrap;
  line-height: 1.6;
}
h3 {
  margin: 20px 0 10px;
  font-size: var(--ui-font-md);
  font-weight: 650;
}
.subsection-title {
  margin: 12px 0 8px;
  font-size: var(--ui-font-sm);
  font-weight: 650;
  color: var(--ui-text);
}
.group {
  margin-bottom: 10px;
}
.group h3 {
  margin: 8px 0 6px;
  font-size: var(--ui-font-hint);
  color: var(--ui-text-muted);
  font-weight: 500;
}
.feats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.feat {
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  padding: 7px 12px;
  display: flex;
  align-items: baseline;
  gap: 8px;
  background: var(--ui-surface);
}
.feat .k {
  color: var(--ui-text-muted);
  font-size: var(--ui-font-hint);
}
.feat .v {
  font-family: var(--ui-font-mono);
  font-weight: 600;
}
.mono {
  font-family: var(--ui-font-mono);
}
</style>
