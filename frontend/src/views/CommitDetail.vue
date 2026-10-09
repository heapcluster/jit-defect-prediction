<template>
  <div>
    <div class="head">
      <el-button
        link
        @click="$router.back()"
      >
        ← 返回列表
      </el-button>
      <h2>提交详情</h2>
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
      <!-- 风险值 -->
      <div class="hero">
        <span
          class="big"
          :style="{ color: riskColor(detail.risk_score) }"
        >
          {{ (detail.risk_score * 100).toFixed(1) }}%
        </span>
        <el-tag :type="riskTag(detail.risk_score)">
          {{ riskLabel(detail.risk_score) }}
        </el-tag>
        <el-tag type="info">
          模型 {{ detail.model_name }}
        </el-tag>
      </div>

      <!-- 元信息 -->
      <el-descriptions
        :column="2"
        border
      >
        <el-descriptions-item label="提交哈希">
          <span class="mono">{{ detail.commit_hash }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="作者">
          {{ detail.author_name }}
        </el-descriptions-item>
        <el-descriptions-item label="提交时间">
          {{ formatTime(detail.committed_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="提交信息">
          {{ detail.message }}
        </el-descriptions-item>
      </el-descriptions>

      <!-- 风险解释 -->
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
          <span class="f">{{ e.feature }}</span>
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
            <span class="v">{{ features[f] ?? '—' }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getCommitDetail } from '../api'

const props = defineProps({
  hash: { type: String, required: true }
})

const detail = ref(null)
const loading = ref(false)
const error = ref('')
const errorCode = ref(0)

// 特征五维分组（docs/pages.md 第 3 节）
const featureGroups = [
  { title: '代码分布', fields: ['ns', 'nd', 'nf', 'entropy'] },
  { title: '规模', fields: ['la', 'ld', 'lt'] },
  { title: '目的', fields: ['fix'] },
  { title: '历史', fields: ['ndev', 'age', 'nuc'] },
  { title: '开发者经验', fields: ['exp', 'rexp', 'sexp'] }
]

const features = computed(() => detail.value?.features || {})
const explanation = computed(() => {
  const list = detail.value?.explanation || []
  // 按 |contribution| 降序，页面只显示前 8 项
  return [...list]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, 8)
})

function riskColor(score) {
  if (score >= 0.5) return '#d9484a'
  if (score >= 0.3) return '#d98a2b'
  return '#4e9b68'
}

function riskTag(score) {
  if (score >= 0.5) return 'danger'
  if (score >= 0.3) return 'warning'
  return 'success'
}

function riskLabel(score) {
  if (score >= 0.5) return '高风险'
  if (score >= 0.3) return '中等风险'
  return '常规'
}

function barWidth(contribution) {
  const pct = Math.min(Math.abs(contribution) / 0.3, 1) * 100
  return pct.toFixed(0) + '%'
}

function signed(v) {
  return (v > 0 ? '+' : '') + v.toFixed(2)
}

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
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

function errText(e) {
  const code = e?.code
  if (code === 40100) return '登录已失效，请重新登录'
  if (code === 40400) return '该提交不存在'
  if (code === 50000) return '服务异常，请稍后重试'
  return e?.message || '请求失败'
}

onMounted(load)
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
.big {
  font-size: 40px;
  font-weight: 700;
  font-family: monospace;
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
  width: 90px;
  font-family: monospace;
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
  width: 56px;
  text-align: right;
  font-family: monospace;
  color: #6b7280;
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
