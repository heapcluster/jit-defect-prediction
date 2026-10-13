<template>
  <div class="page" v-loading="loading">
    <div class="back">
      <el-button link type="primary" @click="router.back()">← 返回风险列表</el-button>
    </div>

    <!-- 契约三 §三.2：提交存在但 prediction 无行 → code=0、risk_score 为 null，不是错误，不得用 0.0 冒充 -->
    <el-alert
      v-if="!loading && detail && detail.risk_score === null"
      type="info"
      :closable="false"
      title="该提交尚未预测：无风险值与特征解释"
    />

    <el-descriptions v-if="detail" :column="3" border class="meta">
      <el-descriptions-item label="风险值">
        <span v-if="detail.risk_score === null" class="risk none">尚未预测</span>
        <span v-else class="risk" :class="riskClass(detail.risk_score)">{{ formatPct(detail.risk_score) }}</span>
      </el-descriptions-item>
      <el-descriptions-item label="模型版本">{{ detail.model_name || '—' }}</el-descriptions-item>
      <el-descriptions-item label="提交哈希">
        <el-tooltip :content="detail.commit_hash" placement="top">
          <span class="hash">{{ shortHash(detail.commit_hash) }}</span>
        </el-tooltip>
      </el-descriptions-item>
      <el-descriptions-item label="作者">{{ detail.author_name || '—' }}</el-descriptions-item>
      <el-descriptions-item label="提交时间">{{ formatTime(detail.committed_at) }}</el-descriptions-item>
      <el-descriptions-item label="提交信息">{{ detail.message || '—' }}</el-descriptions-item>
    </el-descriptions>

    <el-card class="block" shadow="never">
      <template #header>风险解释（SHAP · 只说明推高 / 降低，不解释数值含义）</template>
      <div v-if="explanationTop.length" class="explain">
        <div v-for="row in explanationTop" :key="row.feature" class="explain-row">
          <span class="feature" :title="row.feature">{{ row.feature }}</span>
          <div class="bar-track">
            <div class="bar" :class="row.direction" :style="{ width: barWidth(row.contribution) }" />
          </div>
          <span class="dir" :class="row.direction">
            {{ row.direction === 'increase' ? '推高' : '降低' }}
          </span>
        </div>
      </div>
      <el-empty v-else description="该模型未提供特征解释" />
    </el-card>

    <el-card class="block" shadow="never">
      <template #header>特征值（14 项 · 按 Kamei 五维度分组）</template>
      <div v-if="detail && detail.features" class="features">
        <div v-for="g in FEATURE_GROUPS" :key="g.name" class="feature-group">
          <h4>{{ g.name }}</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item v-for="k in g.keys" :key="k" :label="k">
              {{ formatFeature(detail.features[k]) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
      <!-- 契约三 §三.2：features 为 null 时不得 40400、不得以 0 填充，缺失要可见 -->
      <el-empty v-else description="该提交无特征数据（链路信号，须可见）" />
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getCommitDetail } from '../api'
import { handleError } from '../utils/feedback'
import {
  formatPct,
  riskClass,
  shortHash,
  formatTime,
  formatFeature
} from '../utils/format'
import { FEATURE_GROUPS, MAX_EXPLANATION } from '../constants'

const props = defineProps({ hash: { type: String, required: true } })
const router = useRouter()

const loading = ref(false)
const detail = ref(null)

// 按 |contribution| 降序，只显前 8（pages.md §3）
const explanationTop = computed(() => {
  const list = (detail.value && detail.value.explanation) || []
  return list
    .slice()
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .slice(0, MAX_EXPLANATION)
})

const maxAbsContribution = computed(() => {
  const list = (detail.value && detail.value.explanation) || []
  return list.reduce((m, r) => Math.max(m, Math.abs(r.contribution)), 0)
})

// 条长相对最大 |contribution| 归一，最大占半轨（increase 向右、decrease 向左）
function barWidth(contribution) {
  const max = maxAbsContribution.value
  if (!max) return '0%'
  return `${(Math.abs(contribution) / max) * 50}%`
}

async function load() {
  loading.value = true
  try {
    detail.value = await getCommitDetail(props.hash)
  } catch (err) {
    handleError(err)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.back {
  margin-bottom: -4px;
}
.meta :deep(.el-descriptions__label) {
  width: 90px;
}
.risk {
  font-weight: 600;
}
.risk.high {
  color: #f56c6c;
}
.risk.mid {
  color: #e6a23c;
}
.risk.low {
  color: #409eff;
}
.risk.none {
  color: #909399;
}
.hash {
  font-family: monospace;
  cursor: help;
  border-bottom: 1px dashed var(--el-border-color);
}
.block {
  margin-top: 4px;
}
.explain {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.explain-row {
  display: grid;
  grid-template-columns: 110px 1fr 44px;
  align-items: center;
  gap: 10px;
}
.feature {
  font-family: monospace;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bar-track {
  position: relative;
  height: 14px;
  background: var(--el-fill-color-light);
  border-radius: 2px;
}
/* 中线：increase 向右、decrease 向左（pages.md §3） */
.bar-track::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--el-border-color);
}
.bar {
  position: absolute;
  top: 3px;
  height: 8px;
  border-radius: 1px;
}
.bar.increase {
  left: 50%;
  background: #f56c6c;
}
.bar.decrease {
  right: 50%;
  background: #67c23a;
}
.dir {
  font-size: 12px;
}
.dir.increase {
  color: #f56c6c;
}
.dir.decrease {
  color: #67c23a;
}
.features {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.feature-group h4 {
  margin: 0 0 6px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
