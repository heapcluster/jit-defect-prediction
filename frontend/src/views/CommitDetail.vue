<template>
  <div>
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
          SZZ：引入缺陷
        </el-tag>
        <el-tag
          v-else-if="detail.is_bug_inducing === 0"
          type="success"
          size="small"
        >
          SZZ：非缺陷
        </el-tag>
        <el-tag
          v-else
          type="info"
          size="small"
        >
          无 SZZ 标记
        </el-tag>
      </div>

      <!-- 重新预测：架构 → 模型级联 -->
      <div class="opbar">
        <span class="muted">重新预测：</span>
        <LineModelCascade
          v-model:line="predictLine"
          v-model:model="predictModel"
          :lines="lines"
          model-placeholder="默认模型"
        />
        <el-button
          size="small"
          type="primary"
          :loading="predicting"
          :disabled="forbidden"
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
      <div
        v-if="detail.result_source || detail.stale"
        class="opbar"
      >
        <el-tag
          v-if="detail.result_source"
          size="small"
          :type="detail.result_source === 'computed' ? 'success' : 'info'"
        >
          {{ detail.result_source === 'computed' ? '本次重新计算' : '沿用库中结果' }}
        </el-tag>
        <el-tag
          v-if="detail.stale"
          size="small"
          type="warning"
        >
          版本变化，结果可能过期
        </el-tag>
        <span
          v-if="detail.decision_threshold != null"
          class="muted"
        >阈值 {{ detail.decision_threshold }} · 标签 {{ detail.predicted_label }}</span>
      </div>

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
          <span class="k">信息</span>
          <span class="v msg">{{ detail.message }}</span>
        </div>
      </div>

      <!-- 风险解释 -->
      <template v-if="!isNotPredicted">
        <h3>风险解释</h3>
        <div class="opbar">
          <label for="detail-technique">解释技术</label>
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
          v-if="explainSpace"
          class="muted"
        >
          输出尺度：{{ explainSpace }}；LIME 是局部概率代理系数，不能与 SHAP 数值直接相加。
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
        />
      </template>

      <!-- 缺陷定位（G1-1）：无文件/行级数据，降级到提交级特征归因 -->
      <template v-if="localization">
        <h3>缺陷定位</h3>
        <el-button
          size="small"
          data-testid="detail-open-localization"
          @click="$router.push({ path: '/localization', query: { commit_hash: detail.commit_hash, model_name: detail.model_name } })"
        >
          打开定位及源码工具
        </el-button>
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
                可疑度 {{ Math.round((f.score || 0) * 100) }}%
              </el-tag>
              <span class="muted">{{ f.reasons.join(' · ') }}</span>
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
            <span><i class="dot high" />高可疑 ≥70%</span>
            <span><i class="dot mid" />中 40–70%</span>
            <span><i class="dot low" />低 &lt;40%</span>
          </div>
          <div
            v-if="localization.truncated"
            class="muted"
          >
            仅展示可疑度最高的前若干文件 / hunk 行，已截断
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

      <!-- 14 项特征：中文名为主，悬停看原始字段名 -->
      <h3>14 项特征</h3>
      <div
        v-for="group in featureGroups"
        :key="group.title"
        class="group"
      >
        <h4>{{ group.title }}</h4>
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

      <!-- 修复建议与参考（G1-2）：可执行建议 + 同仓库历史修复提交 -->
      <template v-if="fixReferences">
        <h3>修复建议与参考</h3>
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
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getCommitDetail, getExplainTechniques, postExplain, postPredict } from '../api'
import { ElMessage } from 'element-plus'
import { riskColor } from '../utils/risk'
import { loadModelLines } from '../utils/models'
import { FEATURE_GROUPS, featureLabel } from '../utils/features'
import { errText } from '../utils/errors'
import { formatTime } from '../utils/datetime'
import LineModelCascade from '../components/LineModelCascade.vue'
import RiskTag from '../components/RiskTag.vue'

const props = defineProps({
  hash: { type: String, required: true }
})

const route = useRoute()

const detail = ref(null)
const loading = ref(false)
const error = ref('')
const errorCode = ref(0)

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

// 解释为空是预期：只有 expert 线的树/线性模型能算 SHAP；
// 深度/核模型（tabnet/svm/mlp）与 semantic/fused/e2e 线不提供逐特征归因。
const explanationHint = computed(() => {
  const name = detail.value?.model_name || ''
  if (name.includes('_semantic') || name.includes('_fused') || name.includes('e2e')) {
    return '该模型属于语义 / 融合 / 端到端线，只提供风险分，不提供逐特征归因。'
  }
  if (/^(tabnet|svm|mlp_deep)/.test(name)) {
    return '该模型为深度 / 核模型，当前不提供逐特征归因；可切换到 lr / rf / xgb / lgbm / et 查看解释。'
  }
  return '该模型未提供特征解释'
})

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
  if (value >= 0.7) return '#d9484a'
  if (value >= 0.4) return '#d98a2b'
  return '#4e9b68'
}

function riskTint(score) {
  return lineColor(score) + '1a'
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

async function load() {
  loading.value = true
  error.value = ''
  errorCode.value = 0
  try {
    const model = typeof route.query.model_name === 'string' ? route.query.model_name : undefined
    detail.value = await getCommitDetail(props.hash, model)
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
      explainError.value = err.detail || err.message || '解释服务不可用'
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
  })
})
// 路由参数变化时重载：组件复用时不重载会显示上一条提交
watch(
  () => props.hash,
  () => {
    detail.value = null
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
  font-size: 38px;
  font-weight: 700;
  font-family: monospace;
  line-height: 1;
}
.spacer {
  flex: 1;
}
.muted {
  color: #9aa1ab;
  font-size: 12px;
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
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
  line-height: 1.6;
}
.file-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 2px 0 6px;
  font-size: 12px;
}
.suggestions {
  margin: 8px 0 16px;
  padding: 10px 14px;
  background: var(--el-color-success-light-9);
  border-left: 3px solid var(--el-color-success);
  border-radius: 4px;
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
  font-size: 13px;
}
.e .track {
  flex: 1;
  height: 10px;
  border-radius: 5px;
  background: #eceef2;
  overflow: hidden;
}
.e .track i {
  display: block;
  height: 100%;
  border-radius: 5px;
}
.e .track i.increase {
  background: #d9484a;
}
.e .track i.decrease {
  background: #4e9b68;
}
.e .val {
  width: 68px;
  text-align: right;
  white-space: nowrap;
  font-family: monospace;
  color: #6b7280;
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
  font-size: 12px;
  color: #7c838c;
  margin-bottom: 4px;
  word-break: break-all;
}
.line {
  display: flex;
  gap: 10px;
  padding: 2px 8px;
  border-left: 3px solid transparent;
  font-family: monospace;
  font-size: 12px;
}
.line-no {
  min-width: 36px;
  text-align: right;
  color: #9aa1ab;
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
  color: #909399;
  font-size: 11px;
}
.loc-legend {
  display: flex;
  gap: 16px;
  margin-top: 4px;
  color: #7c838c;
  font-size: 12px;
}
.loc-legend .dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  margin-right: 4px;
}
.loc-legend .dot.high {
  background: #f56c6c;
}
.loc-legend .dot.mid {
  background: #e6a23c;
}
.loc-legend .dot.low {
  background: #67c23a;
}
.loc {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 8px 0 16px;
}
.loc .rank {
  width: 18px;
  font-size: 12px;
  color: #9aa1ab;
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
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 8px 12px;
  background: #fff;
}
.ref-hash {
  color: #7c838c;
  font-size: 12px;
}
.ref-msg {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}
.ref-time {
  color: #9aa1ab;
  font-size: 12px;
  white-space: nowrap;
}
.meta {
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  overflow: hidden;
  margin: 0 0 20px;
}
.meta .row {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid #eef0f4;
}
.meta .row:last-child {
  border-bottom: none;
}
.meta .k {
  color: #7c838c;
  font-size: 13px;
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
  font-size: 15px;
  margin: 18px 0 8px;
}
.group {
  margin-bottom: 10px;
}
.group h4 {
  margin: 8px 0 6px;
  font-size: 12px;
  color: #7c838c;
  font-weight: 500;
}
.feats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.feat {
  border: 1px solid #e2e5ea;
  border-radius: 6px;
  padding: 6px 12px;
  display: flex;
  align-items: baseline;
  gap: 8px;
  background: #fff;
}
.feat .k {
  color: #7c838c;
  font-size: 12px;
}
.feat .v {
  font-family: monospace;
  font-weight: 600;
}
.mono {
  font-family: monospace;
}
</style>
