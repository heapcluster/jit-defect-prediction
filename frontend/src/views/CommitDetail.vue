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

      <!-- 缺陷定位（G1-1）：无文件/行级数据，降级到提交级特征归因 -->
      <template v-if="localization">
        <h3>缺陷定位</h3>
        <el-alert
          :title="localization.notice"
          type="info"
          :closable="false"
          show-icon
          class="loc-notice"
        />
        <!-- 行级定位：新增代码行按提交级缺陷概率分档着色 -->
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
              v-for="l in f.added_lines"
              :key="`${f.path}:${l.number}`"
              class="line"
              :style="{ borderLeftColor: riskColor(detail.risk_score), background: riskTint(detail.risk_score) }"
            >
              <span class="line-no mono">{{ l.number }}</span>
              <span class="line-content">{{ l.content }}</span>
            </div>
          </div>
          <div
            v-if="localization.truncated"
            class="muted"
          >
            仅展示改动最多的前若干文件/行，已截断
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

      <!-- 修复参考（G1-2）：同仓库历史修复提交；无依据时明确空态 -->
      <template v-if="fixReferences">
        <h3>修复参考</h3>
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
          description="暂无历史修复参考"
        />
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { getCommitDetail, postPredict } from '../api'
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

const detail = ref(null)
const loading = ref(false)
const error = ref('')
const errorCode = ref(0)

// 重新预测：架构 → 模型级联
const lines = ref([])
const predictLine = ref('')
const predictModel = ref('')
const predicting = ref(false)
const forbidden = ref(false)

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

// 新增行按提交级风险分着色：8 位 hex（6 位色值 + '1a' ≈ 10% 透明度背景）
function riskTint(score) {
  return riskColor(score) + '1a'
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
      predicted_at: data.predicted_at,
      explanation: data.explanation || [],
      features: data.features || detail.value.features
    }
    ElMessage.success('预测完成')
  } catch (e) {
    // 40100 令牌失效：不给重试，禁用预测按钮
    if (e?.code === 40100) forbidden.value = true
    ElMessage.error(errText(e))
  } finally {
    predicting.value = false
  }
}

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
