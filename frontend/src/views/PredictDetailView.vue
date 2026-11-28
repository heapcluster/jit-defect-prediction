<template>
  <div class="stack">
    <PageHeader title="预测详情" :subtitle="subtitle" eyebrow="Pipeline 04">
      <template #actions>
        <el-button @click="goBack">← 返回预测结果</el-button>
      </template>
    </PageHeader>

    <div v-if="loading" class="stack">
      <SectionCard index="01" title="预测信息">
        <el-skeleton :rows="3" animated />
      </SectionCard>
    </div>

    <SectionCard v-else-if="loadError" index="01" title="预测信息">
      <ErrorState :message="loadError" @retry="load" />
      <template #footer>
        <span class="muted">结果可能已失效，返回列表可重新发起预测。</span>
        <el-button @click="goBack">返回列表</el-button>
      </template>
    </SectionCard>

    <template v-else-if="detail">
      <SectionCard index="01" title="预测信息" description="只读；真实标签仅在有标签数据时显示">
        <div class="meta-grid">
          <div><span>提交哈希</span><strong class="mono">{{ detail.commit_hash }}</strong></div>
          <div><span>提交说明</span><strong>{{ detail.commit_message || '—' }}</strong></div>
          <div><span>作者</span><strong>{{ detail.author_name || '—' }}</strong></div>
          <div><span>提交时间</span><strong>{{ formatTime(detail.commit_time) }}</strong></div>
          <div v-if="detail.actual_label !== null && detail.actual_label !== undefined">
            <span>真实标签</span>
            <strong>{{ detail.actual_label === 1 ? '缺陷' : '正常' }}</strong>
          </div>
          <div><span>模型</span><strong class="mono">{{ detail.model || '—' }}</strong></div>
          <div><span>阈值</span><strong>{{ Number(detail.threshold).toFixed(2) }}</strong></div>
          <div><span>预测概率</span><strong>{{ Number(detail.risk_score).toFixed(4) }}</strong></div>
          <div>
            <span>预测结果</span>
            <strong>
              <span class="pill" :class="detail.predicted_label === 1 ? 'danger' : 'success'">
                {{ detail.predicted_label === 1 ? '缺陷' : '正常' }}
              </span>
            </strong>
          </div>
        </div>
      </SectionCard>

      <SectionCard index="02" title="预测结果解释" description="切换技术后按需计算，刷新页面不保留上次解释">
        <template #aside>
          <el-radio-group v-model="technique" size="small" :disabled="explainLoading" @change="loadExplain">
            <el-radio-button v-for="item in techniques" :key="item.value" :value="item.value">{{ item.label }}</el-radio-button>
          </el-radio-group>
        </template>

        <div v-if="line === 'semantic'" class="hint">语义向量模型不支持 SHAP，请使用 LIME 或置换重要性；贡献表展示前 10 个向量维度。</div>

        <div v-if="explainLoading" class="loading-block">
          <span class="spinner" /> 正在计算特征贡献…
        </div>
        <ErrorState v-else-if="explainError" :message="explainError" @retry="loadExplain" />

        <template v-else-if="explainItems.length">
          <div class="explain-grid" :class="{ single: line === 'semantic' }">
            <el-table :data="explainItems" border size="small" class="explain-table">
              <el-table-column label="特征" width="180">
                <template #default="{ row }"><span class="mono">{{ row.feature }}</span></template>
              </el-table-column>
              <el-table-column label="贡献值" align="right" width="130">
                <template #default="{ row }">{{ Number(row.contribution).toFixed(5) }}</template>
              </el-table-column>
              <el-table-column label="方向" width="100" align="center">
                <template #default="{ row }">
                  <span class="pill" :class="row.direction === 'positive' ? 'danger' : 'success'">
                    {{ row.direction === 'positive' ? '正向' : '负向' }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="line === 'expert'" class="chart-panel">
              <EChart :option="barOption" height="340px" />
            </div>
          </div>
          <div v-if="explainNote" class="pill warning">{{ explainNote }}</div>
        </template>
        <div v-else class="muted">选择解释技术后展示特征贡献。</div>
      </SectionCard>

      <SectionCard index="03" title="缺陷定位与修复" description="基于本地仓库缓存定位高风险改动行，建议由规则模板生成">
        <div v-if="localizeLoading" class="loading-block">
          <span class="spinner" /> 正在解析变更文件…
        </div>
        <div v-else-if="localizeNotice" class="notice">{{ localizeNotice }}</div>
        <ErrorState v-else-if="localizeError" :message="localizeError" @retry="loadLocalize" />
        <div v-else-if="!files.length" class="notice">该提交没有可展示的改动行。</div>

        <div v-else class="files">
          <article v-for="file in files" :key="file.path" class="file-card">
            <button class="file-head" :aria-expanded="expanded === file.path" @click="toggleFile(file.path)">
              <span class="mono file-path">{{ file.path }}</span>
              <span class="pill" :class="file.suspicious_score >= 0.6 ? 'danger' : 'warning'">
                可疑度 {{ Number(file.suspicious_score).toFixed(2) }}
              </span>
              <span class="soft">{{ file.lines.length }} 行改动</span>
              <span class="chevron">{{ expanded === file.path ? '收起 diff' : '展开 diff' }}</span>
            </button>

            <div v-if="expanded === file.path" class="diff">
              <div
                v-for="line in file.lines"
                :key="`${file.path}-${line.no}-${line.type}`"
                class="diff-row"
                :class="[line.type, { suspicious: line.suspicious }]"
              >
                <span class="line-no">{{ line.no }}</span>
                <span class="line-mark">{{ line.type === 'added' ? '+' : line.type === 'removed' ? '−' : ' ' }}</span>
                <span class="line-code">{{ line.content || ' ' }}</span>
                <span v-if="line.suspicious" class="pill danger">可疑</span>
                <p v-if="line.suspicious && line.suggestion" class="suggestion">修复建议：{{ line.suggestion }}</p>
              </div>
            </div>
          </article>
        </div>
      </SectionCard>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PageHeader from '../components/PageHeader.vue'
import SectionCard from '../components/SectionCard.vue'
import ErrorState from '../components/ErrorState.vue'
import EChart from '../components/EChart.vue'
import * as predictApi from '../api/predict'
import { humanError, formatTime } from '../utils/format'

const route = useRoute()
const router = useRouter()

const jobId = String(route.params.jobId || '')
const commitHash = String(route.params.commitHash || '')

const loading = ref(true)
const loadError = ref('')
const detail = ref(null)

const technique = ref('shap')
const explainLoading = ref(false)
const explainError = ref('')
const explainItems = ref([])
const explainNote = ref('')

const localizeLoading = ref(false)
const localizeError = ref('')
const localizeNotice = ref('')
const files = ref([])
const expanded = ref('')

const TECHNIQUE_LABEL = {
  shap: 'SHAP',
  lime: 'LIME',
  permutation: '置换重要性'
}

const line = computed(() => {
  if (detail.value?.line === 'semantic' || detail.value?.line === 'expert') return detail.value.line
  const model = detail.value?.model || ''
  return model.startsWith('semantic-') ? 'semantic' : 'expert'
})

const techniques = computed(() => {
  if (line.value === 'semantic') {
    return [
      { value: 'lime', label: TECHNIQUE_LABEL.lime },
      { value: 'permutation', label: TECHNIQUE_LABEL.permutation }
    ]
  }
  return [
    { value: 'shap', label: TECHNIQUE_LABEL.shap },
    { value: 'lime', label: TECHNIQUE_LABEL.lime },
    { value: 'permutation', label: TECHNIQUE_LABEL.permutation }
  ]
})

const subtitle = computed(() => {
  if (!detail.value) return `${route.params.jobId || '—'} · ${route.params.commitHash || '—'}`
  const model = detail.value.model || '外部模型'
  return `${model} · ${String(detail.value.commit_hash).slice(0, 8)}`
})

const barOption = computed(() => {
  const items = [...explainItems.value].reverse()
  return {
    grid: { left: 104, right: 24, top: 18, bottom: 26 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#eef2f8' } },
      axisLine: { lineStyle: { color: '#cbd5e1' } }
    },
    yAxis: {
      type: 'category',
      data: items.map((item) => item.feature),
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { fontSize: 11 }
    },
    series: [
      {
        type: 'bar',
        data: items.map((item) => ({
          value: item.contribution,
          itemStyle: { color: item.contribution >= 0 ? '#d64545' : '#0f766e', borderRadius: [0, 4, 4, 0] }
        })),
        barMaxWidth: 16
      }
    ]
  }
})

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    detail.value = await predictApi.getDetail(jobId, commitHash)
    technique.value = line.value === 'semantic' ? 'lime' : 'shap'
    await loadExplain()
    await loadLocalize()
  } catch (error) {
    loadError.value = humanError(error)
  } finally {
    loading.value = false
  }
}

async function loadExplain() {
  if (!detail.value) return
  const value = technique.value
  if (line.value === 'semantic' && value === 'shap') {
    technique.value = 'lime'
    return
  }
  explainLoading.value = true
  explainError.value = ''
  explainItems.value = []
  explainNote.value = ''
  try {
    const data = await predictApi.explain({
      job_id: jobId,
      commit_hash: commitHash,
      technique: value
    })
    explainItems.value = data.items || []
    explainNote.value = data.note || ''
  } catch (error) {
    explainError.value = humanError(error)
  } finally {
    explainLoading.value = false
  }
}

async function loadLocalize() {
  localizeError.value = ''
  localizeNotice.value = ''
  files.value = []
  expanded.value = ''
  if (!detail.value?.repo_available) {
    localizeNotice.value = '该数据集来自外部导入，未关联仓库，不支持缺陷定位。'
    return
  }
  localizeLoading.value = true
  try {
    const data = await predictApi.localize({ job_id: jobId, commit_hash: commitHash })
    files.value = data.files || []
    if (files.value.length) expanded.value = files.value[0].path
  } catch (error) {
    const reason = error?.detail?.reason
    if (reason === 'no_repo') {
      localizeNotice.value = '该数据集缺少仓库来源，不支持缺陷定位。'
    } else if (reason === 'commit_missing') {
      localizeNotice.value = '本地仓库缓存缺少该提交，无法展示源码定位。'
    } else {
      localizeError.value = humanError(error)
    }
  } finally {
    localizeLoading.value = false
  }
}

function toggleFile(path) {
  expanded.value = expanded.value === path ? '' : path
}

function goBack() {
  router.push('/predict')
}

onMounted(load)
</script>

<style scoped>
.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}

.meta-grid > div {
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.meta-grid span {
  font-size: 11.5px;
  color: var(--text-soft);
}

.meta-grid strong {
  font-size: 13px;
  word-break: break-all;
}

.hint {
  font-size: 12.5px;
  color: var(--text-soft);
  margin-bottom: 12px;
}

.loading-block {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-muted);
  font-size: 12.5px;
  padding: 18px 0;
}

.spinner {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--border-strong);
  border-top-color: var(--primary);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.explain-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
}

.explain-grid.single {
  grid-template-columns: minmax(0, 1fr);
}

.chart-panel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-muted);
  padding: 10px;
}

.notice {
  padding: 16px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface-muted);
  color: var(--text-muted);
  font-size: 12.5px;
}

.files {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.file-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 14px;
  background: var(--surface-muted);
  border: 0;
  cursor: pointer;
  text-align: left;
  font: inherit;
}

.file-path {
  font-weight: 700;
  color: var(--text);
}

.chevron {
  margin-left: auto;
  font-size: 12px;
  color: var(--primary-strong);
  font-weight: 600;
}

.diff {
  padding: 10px 0;
  overflow-x: auto;
  background: #0f172a;
}

.diff-row {
  display: grid;
  grid-template-columns: 54px 20px minmax(0, 1fr) auto;
  align-items: start;
  gap: 6px;
  padding: 3px 14px;
  font-family: var(--mono);
  font-size: 12px;
  color: #cbd5e1;
  white-space: pre;
}

.diff-row.added {
  background: rgba(34, 197, 94, 0.1);
}

.diff-row.removed {
  background: rgba(239, 68, 68, 0.12);
}

.diff-row.suspicious {
  box-shadow: inset 3px 0 0 #f59e0b;
}

.line-no {
  color: #64748b;
  text-align: right;
  user-select: none;
}

.line-mark {
  color: #94a3b8;
  user-select: none;
}

.line-code {
  white-space: pre-wrap;
  word-break: break-word;
}

.diff-row .pill {
  font-size: 11px;
  padding: 1px 8px;
}

.suggestion {
  grid-column: 2 / -1;
  margin: 4px 0 6px;
  padding: 6px 10px;
  border-radius: 6px;
  background: rgba(245, 158, 11, 0.14);
  color: #fbbf24;
  font-family: var(--font);
  font-size: 12px;
  white-space: normal;
}

@media (max-width: 900px) {
  .explain-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
