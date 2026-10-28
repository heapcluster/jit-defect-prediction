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

    <PageHint text="这条提交是否真的引入缺陷？看风险与解释因子，确认后标记 —— 标记会用于质量校准。">
      <!-- 三态必须分清：撤销（无标签）≠ 确认非缺陷（计入 tn/fp） -->
      <el-button
        v-if="label"
        size="small"
        :loading="labeling"
        @click="mark(null)"
      >
        撤销标记
      </el-button>
      <el-button
        size="small"
        :loading="labeling"
        @click="mark(false)"
      >
        确认非缺陷
      </el-button>
      <el-button
        size="small"
        type="danger"
        plain
        :loading="labeling"
        @click="mark(true)"
      >
        标记为引入缺陷
      </el-button>
    </PageHint>

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

    <!-- 骨架屏用 el-skeleton：空 div + 转圈只是「一片空白」，看不出正在加载什么 -->
    <el-skeleton
      v-if="loading"
      :rows="6"
      animated
      class="skeleton"
    />

    <template v-if="detail">
      <!-- 风险与确认状态：一行给结论，避免同一信息重复两遍 -->
      <div class="hero">
        <!-- 未预测时只留 RiskTag 的「未预测」，不再同时显示一个大字号「—」 -->
        <span
          v-if="!isNotPredicted"
          class="big"
          :style="{ color: riskColor(detail.risk_score) }"
        >
          {{ `${(detail.risk_score * 100).toFixed(1)}%` }}
        </span>
        <RiskTag
          :level="detail.risk_level"
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
        <template v-if="label">
          <el-tag
            :type="label.is_defect ? 'danger' : 'success'"
            size="small"
          >
            {{ label.is_defect ? '已确认：引入缺陷' : '已确认：非缺陷' }}
          </el-tag>
          <span class="muted">标记于 {{ formatDateTime(label.labeled_at) }}</span>
        </template>
        <el-tag
          v-else
          type="info"
          size="small"
        >
          未确认
        </el-tag>
      </div>

      <!-- 重新预测 -->
      <div class="opbar">
        <span class="muted">重新预测：</span>
        <el-select
          v-model="predictModel"
          placeholder="默认最新模型"
          clearable
          size="small"
          style="width: 180px"
        >
          <el-option
            v-for="m in models"
            :key="m"
            :label="m"
            :value="m"
          />
        </el-select>
        <el-button
          size="small"
          type="primary"
          :loading="predicting"
          :disabled="forbidden"
          @click="predict"
        >
          预测
        </el-button>
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
          <span class="k">信息</span>
          <span class="v msg">{{ detail.message }}</span>
        </div>
      </div>

      <!-- 风险解释 -->
      <template v-if="!isNotPredicted">
        <h3>风险解释</h3>
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
          description="该模型未提供特征解释"
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
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getCommitDetail, postPredict, putCommitLabel } from '../api'
import { ElMessage } from 'element-plus'
import { riskColor } from '../utils/risk'
import { loadThresholds } from '../utils/thresholds'
import { MODELS } from '../utils/models'
import { FEATURE_GROUPS, featureLabel } from '../utils/features'
import { errText } from '../utils/errors'
import { formatTime, formatDateTime } from '../utils/datetime'
import PageHint from '../components/PageHint.vue'
import RiskTag from '../components/RiskTag.vue'

const props = defineProps({
  hash: { type: String, required: true }
})

const detail = ref(null)
const loading = ref(false)
const error = ref('')
const errorCode = ref(0)

// 重新预测
const models = MODELS
const predictModel = ref('')
const predicting = ref(false)
const forbidden = ref(false)

// 人工反馈：把事后确认回流成标签
const labeling = ref(false)
const label = computed(() => detail.value?.label || null)

const featureGroups = FEATURE_GROUPS

const features = computed(() => detail.value?.features || {})
// 契约三 §3：提交存在但无预测记录时 risk_score 为 null
const isNotPredicted = computed(() => detail.value?.risk_score == null)
const explanation = computed(() => {
  const list = detail.value?.explanation || []
  // 按 |contribution| 降序，只显示前 8 项
  return [...list]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, 8)
})

// 按本次展示项的最大 |contribution| 归一：固定刻度会让真实贡献值全部顶格，条长失去区分度
const maxContribution = computed(() =>
  Math.max(...explanation.value.map((e) => Math.abs(e.contribution)), 0.000001)
)

function barWidth(contribution) {
  const pct = (Math.abs(contribution) / maxContribution.value) * 100
  return `${pct.toFixed(0)}%`
}

function signed(v) {
  return (v > 0 ? '+' : '') + v.toFixed(2)
}

// 特征值保留 4 位小数：原始值有 10 位以上，全量显示只会干扰阅读
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
      features: data.features || detail.value.features
    }
    // 回填下拉：默认模型时后端实际用的是哪个，下拉就显示哪个（切换后立刻可核对）
    predictModel.value = data.model_name
    ElMessage.success('预测完成')
  } catch (e) {
    // 40100 令牌失效：不给重试，禁用预测按钮
    if (e?.code === 40100) forbidden.value = true
    ElMessage.error(errText(e))
  } finally {
    predicting.value = false
  }
}

// mark(null) = 撤销（删除标签行）；mark(false) = 确认非缺陷（计入质量指标）
async function mark(isDefect) {
  if (!detail.value) return
  labeling.value = true
  try {
    const data = await putCommitLabel(detail.value.commit_hash, isDefect)
    detail.value = { ...detail.value, label: data.is_defect == null ? null : data }
    if (isDefect === null) ElMessage.success('已撤销标记')
    else ElMessage.success(isDefect ? '已标记为引入缺陷' : '已确认非缺陷')
  } catch (e) {
    ElMessage.error(errText(e))
  } finally {
    labeling.value = false
  }
}

onMounted(() => {
  load()
  loadThresholds()
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
