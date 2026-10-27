<template>
  <div>
    <PageHint text="按风险从高到低看提交：点一行看解释，确认后标记是否真的引入缺陷。">
      <el-button
        size="small"
        :loading="catching"
        @click="catchup"
      >
        补齐缺口
      </el-button>
      <el-button
        size="small"
        type="primary"
        @click="load(1)"
      >
        刷新
      </el-button>
    </PageHint>

    <!-- 概览：三张卡各说一件事，条数已在表格与分页器里，不再重复 -->
    <div class="stats">
      <StatCard
        label="已人工确认"
        :value="health ? health.labeled_count : '—'"
        hint="可用于质量校准"
      />
      <StatCard
        label="已预测覆盖"
        :value="coverageLabel"
        :hint="coverageHint"
      />
      <StatCard
        label="服务状态"
        :value="statusLabel"
        :value-color="statusColor"
        :hint="statusHint"
      />
    </div>

    <el-form
      :inline="true"
      class="filters"
    >
      <el-form-item label="模型">
        <el-select
          v-model="filters.model_name"
          clearable
          placeholder="默认模型"
          style="width: 150px"
        >
          <el-option
            v-for="m in models"
            :key="m"
            :label="m"
            :value="m"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="最低风险">
        <el-input-number
          v-model="filters.min_risk"
          :min="0"
          :max="1"
          :step="0.1"
          :precision="1"
          style="width: 120px"
        />
      </el-form-item>
      <el-form-item label="时间">
        <el-date-picker
          v-model="timeRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          style="width: 240px"
        />
      </el-form-item>
      <el-form-item label="仅看已确认">
        <el-switch v-model="filters.has_label" />
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          @click="load(1)"
        >
          查询
        </el-button>
        <el-button @click="reset">
          重置
        </el-button>
      </el-form-item>
    </el-form>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      class="mb"
      :closable="false"
    >
      <el-button
        v-if="retryable"
        size="small"
        text
        @click="load(filters.page)"
      >
        重试
      </el-button>
    </el-alert>

    <el-table
      v-loading="loading"
      :data="items"
      row-key="commit_hash"
      class="risk-table"
      @row-click="goDetail"
    >
      <el-table-column
        label="风险"
        width="180"
      >
        <template #default="{ row }">
          <div class="risk-cell">
            <RiskTag
              :score="row.risk_score"
              effect="dark"
            />
            <span
              class="risk-pct"
              :style="{ color: riskColor(row.risk_score) }"
            >
              {{ (row.risk_score * 100).toFixed(1) }}%
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        label="提交"
        width="110"
      >
        <template #default="{ row }">
          <el-tooltip
            :content="row.commit_hash"
            placement="top"
          >
            <span
              class="mono"
              @click.stop="copyHash(row.commit_hash)"
            >
              {{ row.commit_hash.slice(0, 8) }}
            </span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column
        prop="author_name"
        label="作者"
        width="130"
        show-overflow-tooltip
      />
      <el-table-column
        label="时间"
        width="170"
      >
        <template #default="{ row }">
          {{ formatTime(row.committed_at) }}
        </template>
      </el-table-column>
      <el-table-column
        label="提交信息"
        prop="message"
        show-overflow-tooltip
      />
    </el-table>

    <!-- 空库：给一条明确的「从哪开始」，而不是一堆说明 -->
    <el-card
      v-if="showBootstrap"
      class="boot"
      shadow="never"
    >
      <h3>还没有数据</h3>
      <p class="boot-desc">
        先同步最近若干条提交：逐条现算特征并预测落库，约 15 秒/条。
      </p>
      <div class="boot-row">
        <el-select
          v-model="syncCount"
          style="width: 140px"
          :disabled="syncing"
        >
          <el-option
            v-for="n in [10, 30, 50]"
            :key="n"
            :label="`最近 ${n} 条`"
            :value="n"
          />
        </el-select>
        <el-button
          type="primary"
          :loading="syncing"
          @click="runSync"
        >
          开始同步
        </el-button>
        <span class="boot-tip">前提：backend/.env 已配置 SOURCE_REPO</span>
      </div>
      <el-progress
        v-if="syncing"
        :percentage="syncPct"
        class="boot-progress"
      />
      <p
        v-if="syncMsg"
        class="sync-msg"
      >
        {{ syncMsg }}
      </p>
    </el-card>

    <el-empty
      v-else-if="!loading && !error && items.length === 0"
      description="当前筛选条件下没有提交"
    >
      <el-button
        size="small"
        @click="reset"
      >
        清空筛选
      </el-button>
    </el-empty>

    <el-pagination
      v-if="total > 0"
      class="pager"
      layout="prev, pager, next, total"
      :total="total"
      :page-size="filters.size"
      :current-page="filters.page"
      @current-change="load"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  getCommits,
  postSync,
  getCommitsCoverage,
  postSyncCatchup,
  subscribeSyncProgress,
  getHealth
} from '../api'
import { ElMessage } from 'element-plus'
import { riskColor } from '../utils/risk'
import { MODELS } from '../utils/models'
import { errText, isRetryable } from '../utils/errors'
import { formatTime } from '../utils/datetime'
import StatCard from '../components/StatCard.vue'
import PageHint from '../components/PageHint.vue'
import RiskTag from '../components/RiskTag.vue'

const router = useRouter()
const route = useRoute()

// 模型清单与后端 feature_order.txt 的 [models] 段、utils/models.js 保持一致
const models = MODELS

const filters = reactive({
  model_name: '',
  min_risk: null,
  has_label: false,
  page: 1,
  size: 20
})
const timeRange = ref([])
const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const retryable = ref(false)

// ── 运行状态（observability）──
const health = ref(null)
function loadHealth() {
  getHealth()
    .then((d) => {
      health.value = d
    })
    .catch(() => {})
}
const statusLabel = computed(() => {
  if (!health.value) return '—'
  return health.value.status === 'ok' ? '正常' : '降级'
})
const statusColor = computed(() => (health.value?.status === 'ok' ? '#4e9b68' : '#d98a2b'))
const statusHint = computed(() => {
  if (!health.value) return '状态未知'
  return `模型 ${health.value.models_loaded} 个 · DB ${health.value.db === 'up' ? '正常' : '异常'}`
})

// ── 已预测覆盖 + 补齐到最新 ──
const catching = ref(false)
const coverage = ref([])
const coverageLabel = computed(() => {
  if (!coverage.value.length) return '—'
  const picked =
    coverage.value.find((c) => c.model_name === filters.model_name) || coverage.value[0]
  const start = picked.start ? picked.start.slice(0, 10) : '—'
  const end = picked.end ? picked.end.slice(0, 10) : '—'
  return `${start} ~ ${end}`
})
const coverageHint = computed(() =>
  coverage.value.length ? `${coverage.value.length} 个模型` : '尚无预测'
)
function loadCoverage() {
  getCommitsCoverage()
    .then((d) => {
      coverage.value = d.items || []
    })
    .catch(() => {})
}
function catchup() {
  catching.value = true
  const ctrl = subscribeSyncProgress((s) => {
    if (s.total) syncPct.value = Math.round((s.done / s.total) * 100)
    syncMsg.value = `补齐中 ${s.done}/${s.total}`
  })
  postSyncCatchup()
    .then(() => {
      ElMessage.success('已补齐到最新')
      loadCoverage()
      load(1)
    })
    .catch((e) => {
      ElMessage.error(errText(e))
    })
    .finally(() => {
      catching.value = false
      ctrl.abort()
    })
}

// ── 空库引导：分批同步，绝不提前灌库 ──
const syncing = ref(false)
const syncCount = ref(10)
const syncPct = ref(0)
const syncMsg = ref('')

const hasFilter = computed(
  () =>
    !!(
      filters.model_name ||
      filters.min_risk != null ||
      filters.has_label ||
      (timeRange.value && timeRange.value.length)
    )
)
const showBootstrap = computed(
  () => !loading.value && !error.value && !hasFilter.value && items.value.length === 0
)

async function runSync() {
  syncing.value = true
  syncPct.value = 0
  let done = 0
  try {
    while (done < syncCount.value) {
      const batch = Math.min(10, syncCount.value - done)
      await postSync(batch)
      done += batch
      syncPct.value = Math.round((done / syncCount.value) * 100)
      syncMsg.value = `已落库 ${done}/${syncCount.value} 条`
    }
    ElMessage.success(`同步完成，共 ${done} 条`)
    await load(1)
  } catch (e) {
    ElMessage.error(errText(e))
    syncMsg.value = `中断：已落库 ${done} 条，可再次点击继续`
  } finally {
    syncing.value = false
  }
}

// 最新请求标识：并发时丢弃过期响应，避免快速翻页时旧响应覆盖新结果
let requestId = 0

async function load(page = filters.page) {
  const id = ++requestId
  filters.page = page
  loading.value = true
  error.value = ''
  retryable.value = false
  try {
    const data = await getCommits({
      page: filters.page,
      size: filters.size,
      model_name: filters.model_name || undefined,
      min_risk: filters.min_risk ?? undefined,
      start_time: timeRange.value?.[0] || undefined,
      end_time: timeRange.value?.[1] || undefined,
      has_label: filters.has_label || undefined
    })
    if (id !== requestId) return
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    if (id !== requestId) return
    items.value = []
    total.value = 0
    error.value = errText(e)
    retryable.value = isRetryable(e)
  } finally {
    if (id === requestId) loading.value = false
  }
}

function reset() {
  filters.model_name = ''
  filters.min_risk = null
  filters.has_label = false
  timeRange.value = []
  load(1)
}

// 点击复制提交哈希（.stop 阻止冒泡，避免触发整行跳详情）
async function copyHash(hash) {
  try {
    await navigator.clipboard.writeText(hash)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error(`复制失败：${hash}`)
  }
}

function goDetail(row) {
  router.push(`/commit/${row.commit_hash}`)
}

// 从 route.query 同步时间范围（趋势下钻跳转带回 start_time/end_time）
function applyQueryAndLoad() {
  const { start_time, end_time } = route.query
  timeRange.value = start_time && end_time ? [start_time, end_time] : []
  filters.page = 1
  load(1)
}

onMounted(() => {
  applyQueryAndLoad()
  loadCoverage()
  loadHealth()
})

watch(() => route.query, applyQueryAndLoad)
</script>

<style scoped>
.stats {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.filters {
  margin-bottom: 4px;
}
.mb {
  margin-bottom: 12px;
}
.risk-table {
  cursor: pointer;
  margin-top: 8px;
}
.risk-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.risk-pct {
  font-family: monospace;
  font-weight: 600;
  white-space: nowrap;
}
.mono {
  font-family: monospace;
}
.boot {
  margin-bottom: 16px;
}
.boot h3 {
  margin: 0 0 8px;
  font-size: 15px;
}
.boot-desc {
  margin: 0 0 12px;
  color: #6b7280;
  line-height: 1.6;
}
.boot-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.boot-tip {
  color: #9aa1ab;
  font-size: 12px;
}
.boot-progress {
  margin-top: 10px;
}
.sync-msg {
  margin: 6px 0 0;
  color: #6b7280;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
