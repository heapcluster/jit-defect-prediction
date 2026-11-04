<template>
  <div>
    <!-- 同步范围行：只用于「刷新」，与下方查询栏互不影响 -->
    <el-form
      :inline="true"
      class="filters sync-row"
    >
      <el-form-item label="同步范围">
        <LineModelCascade
          v-model:line="syncLine"
          v-model:model="syncModel"
          :lines="lines"
          model-placeholder="全部在线模型"
        />
        <el-date-picker
          v-model="syncTime"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          style="width: 240px; margin-left: 8px"
        />
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          :loading="syncing"
          @click="refresh"
        >
          刷新
        </el-button>
        <span
          v-if="syncMsg"
          class="sync-msg"
        >{{ syncMsg }}</span>
      </el-form-item>
    </el-form>

    <!-- 查询栏：只查已入库数据，不触发计算 -->
    <el-form
      :inline="true"
      class="filters"
    >
      <el-form-item label="搜索">
        <el-input
          v-model="filters.q"
          placeholder="哈希/作者/提交信息"
          clearable
          maxlength="64"
          style="width: 200px"
          @keyup.enter="load(1)"
        />
      </el-form-item>
      <el-form-item label="架构 / 模型">
        <LineModelCascade
          v-model:line="filters.line"
          v-model:model="filters.model_name"
          :lines="lines"
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

    <el-empty
      v-if="!loading && !error && items.length === 0"
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
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getCommits, postSync, getSyncStatus } from '../api'
import { ElMessage } from 'element-plus'
import { riskColor } from '../utils/risk'
import { loadModelLines } from '../utils/models'
import { errText, isRetryable } from '../utils/errors'
import { formatTime } from '../utils/datetime'
import LineModelCascade from '../components/LineModelCascade.vue'
import RiskTag from '../components/RiskTag.vue'

const router = useRouter()
const route = useRoute()

// 架构 → 模型层级（GET /api/models）
const lines = ref([])
function loadLines() {
  loadModelLines().then((l) => {
    lines.value = l
  })
}

// 同步范围行（只给「刷新」）
const syncLine = ref('')
const syncModel = ref('')
const syncTime = ref([])

// 查询栏
const filters = reactive({
  q: '',
  line: '',
  model_name: '',
  page: 1,
  size: 20
})
const timeRange = ref([])

const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const retryable = ref(false)

// 最新请求标识：并发时丢弃过期响应
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
      q: filters.q.trim() || undefined,
      model_name: filters.model_name || undefined,
      start_time: timeRange.value?.[0] || undefined,
      end_time: timeRange.value?.[1] || undefined
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
  filters.q = ''
  filters.line = ''
  filters.model_name = ''
  timeRange.value = []
  load(1)
}

// 查询栏切换模型立即重查（与模型性能看板一致）：否则选完模型还得再点一次「查询」
watch(() => filters.model_name, () => load(1))

// ── 刷新：按同步范围行调 /api/sync，异步轮 status，完成后按查询栏条件重查 ──
const syncing = ref(false)
const syncMsg = ref('')
let pollTimer = null

async function refresh() {
  if (syncing.value) return
  syncing.value = true
  syncMsg.value = ''
  try {
    await postSync({
      line: syncLine.value || undefined,
      modelName: syncModel.value || undefined,
      startTime: syncTime.value?.[0] || undefined,
      endTime: syncTime.value?.[1] || undefined
    })
    await pollUntilIdle()
    ElMessage.success('同步完成')
  } catch (e) {
    ElMessage.error(errText(e))
  } finally {
    syncing.value = false
    stopPolling()
    syncMsg.value = ''
    load(1)
  }
}

function pollUntilIdle() {
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const s = await getSyncStatus()
        syncMsg.value = s.total ? `同步中 ${s.done}/${s.total}` : '同步中…'
        if (!s.running) return resolve()
      } catch (e) {
        return reject(e)
      }
      pollTimer = setTimeout(tick, 2000)
    }
    tick()
  })
}

function stopPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

// 点击复制提交哈希（.stop 阻止冒泡）
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

// 从 route.query 同步筛选条件（趋势下钻带回 start_time/end_time / model_name 深链）
function applyQueryAndLoad() {
  const { start_time, end_time, model_name, q } = route.query
  timeRange.value = start_time && end_time ? [start_time, end_time] : []
  filters.model_name = typeof model_name === 'string' ? model_name : ''
  filters.q = typeof q === 'string' ? q : ''
  filters.page = 1
  load(1)
}

onMounted(() => {
  loadLines()
  applyQueryAndLoad()
})

watch(() => route.query, applyQueryAndLoad)
</script>

<style scoped>
.filters {
  margin-bottom: 4px;
}
.sync-row {
  background: #f7f8fa;
  border-radius: 8px;
  padding: 8px 12px 0;
}
.sync-msg {
  margin-left: 10px;
  color: #6b7280;
  font-size: 13px;
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
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
