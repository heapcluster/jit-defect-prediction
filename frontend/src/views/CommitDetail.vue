<template>
  <div>
    <div class="head">
      <el-button
        link
        @click="$router.back()"
      >
        ← 返回列表
      </el-button>
    </div>

    <!-- 请求失败 -->
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
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

    <div
      v-if="loading"
      v-loading="loading"
      class="skeleton"
    />

    <template v-if="detail">
      <!-- 风险值：risk_score 为 null 表示尚未预测（契约三 §3），MUST NOT 冒充 0.0 -->
      <div class="hero">
        <template v-if="isNotPredicted">
          <span class="big unpredicted">尚未预测</span>
          <el-tag type="info">
            尚未预测
          </el-tag>
        </template>
        <template v-else>
          <span
            class="big"
            :style="{ color: riskColor(detail.risk_score) }"
          >
            {{ (detail.risk_score * 100).toFixed(1) }}%
          </span>
          <el-tag :type="riskTag(detail.risk_score)">
            {{ riskLabel(detail.risk_score) }}
          </el-tag>
        </template>
        <el-tag
          v-if="detail.model_name"
          type="info"
        >
          模型 {{ detail.model_name }}
        </el-tag>
      </div>

      <!-- 重新预测 -->
      <div class="predict-bar">
        <el-select
          v-model="predictModel"
          placeholder="选择模型（默认取最新模型）"
          style="width: 200px"
        >
          <el-option
            v-for="m in models"
            :key="m"
            :label="m"
            :value="m"
          />
        </el-select>
        <el-button
          type="primary"
          :loading="predicting"
          :disabled="forbidden"
          @click="predict"
        >
          重新预测
        </el-button>
        <span
          v-if="detail.predicted_at"
          class="predicted-at"
        >
          预测时间 {{ formatDateTime(detail.predicted_at) }}
        </span>
      </div>

      <!-- 人工反馈闭环：把「这条提交到底有没有引入缺陷」回流成标签（feedback capability）。
           撤销 = 再次提交 is_defect=false（保留「已确认非缺陷」的事实，不删历史标签行） -->
      <div class="feedback-bar">
        <span class="k">人工确认</span>
        <el-tag
          v-if="label"
          :type="label.is_defect ? 'danger' : 'success'"
        >
          {{ label.is_defect ? '已确认：引入缺陷' : '已确认：非缺陷' }}
        </el-tag>
        <el-tag
          v-else
          type="info"
        >
          未标记
        </el-tag>
        <el-button
          size="small"
          :type="label && label.is_defect ? 'default' : 'danger'"
          :loading="labeling"
          @click="mark(true)"
        >
          标记为引入缺陷
        </el-button>
        <el-button
          v-if="label"
          size="small"
          :loading="labeling"
          @click="mark(false)"
        >
          撤销标记
        </el-button>
        <span
          v-if="label && label.labeled_at"
          class="predicted-at"
        >
          标记于 {{ formatDateTime(label.labeled_at) }}
        </span>
      </div>

      <!-- 元信息：label 固定宽度、值自动换行（提交信息常有换行，表格布局会被压成竖排） -->
      <div class="meta">
        <div class="row">
          <span class="k">提交哈希</span>
          <span class="v mono">{{ detail.commit_hash }}</span>
        </div>
        <div class="row">
          <span class="k">作者</span>
          <span class="v">{{ detail.author_name }}</span>
        </div>
        <div class="row">
          <span class="k">提交时间</span>
          <span class="v">{{ formatTime(detail.committed_at) }}</span>
        </div>
        <div class="row">
          <span class="k">提交信息</span>
          <span class="v msg">{{ detail.message }}</span>
        </div>
      </div>

      <!-- 风险解释：尚未预测时整区不显示（「未提供解释」空态只在 risk_score 非空时出） -->
      <template v-if="!isNotPredicted">
        <h3>风险解释（为什么被判高风险）</h3>
        <div
          v-if="explanation.length"
          class="expl"
        >
          <div
            v-for="e in explanation"
            :key="e.feature"
            class="e"
          >
            <!-- 因子中文名（app.explain.FEATURE_LABELS）；hover tooltip 保留原始缩写 -->
            <el-tooltip
              :content="e.feature"
              placement="top"
            >
              <span class="f">{{ e.label || e.feature }}</span>
            </el-tooltip>
            <div class="track">
              <i
                :class="e.direction"
                :style="{ width: barWidth(e.contribution) }"
              />
            </div>
            <span class="val">
              {{ signed(e.contribution) }}
            </span>
          </div>
        </div>
        <el-empty
          v-else
          description="该模型未提供特征解释"
        />
      </template>

      <!-- 14 项特征 -->
      <h3>14 项特征</h3>
      <div
        v-for="group in featureGroups"
        :key="group.title"
        class="group"
      >
        <h4>{{ group.title }}</h4>
        <div class="feats">
          <div
            v-for="f in group.fields"
            :key="f"
            class="feat"
          >
            <span class="k">{{ f }}</span>
            <span class="v">{{ featureValue(features[f]) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getCommitDetail, postPredict, putCommitLabel } from '../api'
import { ElMessage } from 'element-plus'
import { riskColor, riskTag, riskLabel } from '../utils/risk'
import { MODELS } from '../utils/models'
import { FEATURE_GROUPS } from '../utils/features'
import { errText } from '../utils/errors'
import { formatTime, formatDateTime } from '../utils/datetime'

const props = defineProps({
  hash: { type: String, required: true }
})

const detail = ref(null)
const loading = ref(false)
const error = ref('')
const errorCode = ref(0)

// 重新预测：模型下拉（实际交付的 3 个 .pkl，后端 model_registry 加载的版本名）
const models = MODELS
const predictModel = ref('')
const predicting = ref(false)
const forbidden = ref(false)

// 人工反馈闭环（feedback capability）：把预测的事后确认回流成标签
const labeling = ref(false)
const label = computed(() => detail.value?.label || null)

const featureGroups = FEATURE_GROUPS

const features = computed(() => detail.value?.features || {})
// 契约三 §3：提交存在但无预测记录时 risk_score 为 null，前端按 null 渲染「尚未预测」
const isNotPredicted = computed(() => detail.value?.risk_score == null)
const explanation = computed(() => {
  const list = detail.value?.explanation || []
  // 按 |contribution| 降序，页面只显示前 8 项
  return [...list]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, 8)
})

// 按本次展示项的最大 |contribution| 归一：固定刻度（如 0.3）会让真实贡献值全部顶格，
// 条长就失去区分度（本机实测 nf=+2.30 时前 8 项全是 100%）。
const maxContribution = computed(() =>
  Math.max(...explanation.value.map((e) => Math.abs(e.contribution)), 0.000001)
)

function barWidth(contribution) {
  const pct = (Math.abs(contribution) / maxContribution.value) * 100
  return pct.toFixed(0) + '%'
}

function signed(v) {
  return (v > 0 ? '+' : '') + v.toFixed(2)
}

// 特征值保留 4 位小数：契约二的 ln/归一化值有 10 位以上，全量显示只会干扰阅读
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
    detail.value = await getCommitDetail(props.hash)
  } catch (e) {
    detail.value = null
    errorCode.value = e?.code || 0
    error.value = errText(e)
  } finally {
    loading.value = false
  }
}

// 重新预测：POST /api/predict，刷新 risk_score / model_name / explanation / predicted_at
async function predict() {
  if (!detail.value) return
  predicting.value = true
  try {
    const data = await postPredict(detail.value.commit_hash, predictModel.value || undefined)
    detail.value = {
      ...detail.value,
      risk_score: data.risk_score,
      model_name: data.model_name,
      explanation: data.explanation || [],
      features: data.features || detail.value.features,
      predicted_at: data.predicted_at || null
    }
    ElMessage.success('预测完成')
  } catch (e) {
    // 40100 令牌失效：按 pages.md §5 不给重试，禁用重新预测按钮
    if (e?.code === 40100) forbidden.value = true
    ElMessage.error(errText(e))
  } finally {
    predicting.value = false
  }
}

// 人工反馈：标记为引入缺陷 / 撤销（撤销 = is_defect=false，保留「已确认非缺陷」事实）
async function mark(isDefect) {
  if (!detail.value) return
  labeling.value = true
  try {
    const data = await putCommitLabel(detail.value.commit_hash, isDefect)
    detail.value = { ...detail.value, label: data }
    ElMessage.success(isDefect ? '已标记为引入缺陷' : '已撤销标记')
  } catch (e) {
    ElMessage.error(errText(e))
  } finally {
    labeling.value = false
  }
}

onMounted(load)
// 路由参数变化时重载：/commit/:hash 换 hash 时组件会复用，
// 不重载就会显示上一条提交的详情（2026-10-25 修复）
watch(() => props.hash, () => {
  detail.value = null
  errorCode.value = 0
  load()
})
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
  align-items: center;
  gap: 14px;
  margin: 16px 0;
}
.predict-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 16px;
}
.big {
  font-size: 40px;
  font-weight: 700;
  font-family: monospace;
}
.unpredicted {
  color: #7c838c;
  font-size: 24px;
  font-weight: 500;
}
.expl {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 8px 0 16px;
}
.e {
  display: flex;
  align-items: center;
  gap: 10px;
}
.feedback-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 16px;
}
.feedback-bar .k {
  color: #6b7280;
  font-size: 13px;
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
.meta {
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  overflow: hidden;
  margin: 0 0 20px;
}
.meta .row {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid #eef0f4;
}
.meta .row:last-child {
  border-bottom: none;
}
.meta .k {
  color: #6b7280;
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
.group {
  margin-bottom: 12px;
}
.group h4 {
  margin: 8px 0 6px;
  font-size: 13px;
  color: #6b7280;
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
  gap: 6px;
}
.feat .k {
  font-family: monospace;
  color: #3b5bdb;
}
.feat .v {
  font-family: monospace;
  font-weight: 600;
}
.mono {
  font-family: monospace;
}
</style>
