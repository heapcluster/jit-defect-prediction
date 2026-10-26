<template>
  <div>
    <!-- 筛选栏 -->
    <el-form
      :inline="true"
      class="filters"
    >
      <el-form-item label="模型">
        <el-select
          v-model="filters.model_name"
          clearable
          placeholder="全部模型"
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
        />
      </el-form-item>
      <el-form-item label="时间范围">
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
          type="success"
          :loading="catching"
          @click="catchup"
        >
          补齐到最新
        </el-button>
        <el-button
          type="primary"
          @click="load(1)"
        >
          查询
        </el-button>
        <el-button @click="reset">
          清空筛选
        </el-button>
      </el-form-item>
    </el-form>

    <!-- 请求失败：三态之一，按错误码区分 -->
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      class="mb"
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

    <!-- 已预测覆盖：让用户知晓缺口，通过「补齐到最新」由系统补齐（日期筛选只用于查看，不触发预测） -->
    <el-alert
      v-if="coverageText"
      type="info"
      :closable="false"
      class="mb"
    >
      <span>{{ coverageText }}</span>
      <el-button
        size="small"
        text
        type="success"
        :loading="catching"
        @click="catchup"
      >
        补齐到最新
      </el-button>
    </el-alert>

    <!-- 表格 -->
    <el-table
      v-loading="loading"
      :data="items"
      row-key="commit_hash"
      class="risk-table"
      @row-click="goDetail"
    >
      <el-table-column
        label="风险"
        width="150"
      >
        <template #default="{ row }">
          <div class="risk-cell">
            <div class="risk-bar">
              <i
                :style="{
                  width: (row.risk_score * 100).toFixed(0) + '%',
                  background: riskColor(row.risk_score)
                }"
              />
            </div>
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
        label="提交哈希"
        width="120"
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
        width="140"
        show-overflow-tooltip
      />
      <el-table-column
        label="提交时间"
        width="175"
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

    <!-- 空库 / 空筛选：给「按需现算」的加载台，杜绝任何提前灌库 -->
    <el-card
      v-if="showBootstrap"
      class="boot"
      shadow="never"
    >
      <h3>数据库里还没有提交</h3>
      <p class="boot-desc">
        数据来自 Camel git 历史：<b>逐条现算 14 项特征 → 真实模型预测 → 落库</b>，
        实测每条约 15 秒。不会预先批量灌库，你同步多少条，页面就有多少条。
      </p>
      <p class="boot-desc">
        前提：backend/.env 已配 SOURCE_REPO（本地 Camel 索引，命令：python infra/clone_camel_history.py --repo apache/camel --path &lt;目录&gt;）。
      </p>
      <div class="boot-row">
        <el-select
          v-model="syncCount"
          style="width: 150px"
          :disabled="syncing"
        >
          <el-option
            v-for="n in [10, 30, 50]"
            :key="n"
            :label="`最新 ${n} 条（约 ${Math.round(n * 15 / 60)} 分钟）`"
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

    <!-- 空数据（有筛选时）：三态之一，不是错误 -->
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

    <!-- 分页 -->
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
import { getCommits, postSync, getCommitsCoverage, postSyncCatchup, subscribeSyncProgress } from '../api'
import { ElMessage } from 'element-plus'
import { riskColor, riskLevel } from '../utils/risk'
import { MODELS } from '../utils/models'
import { errText, isRetryable } from '../utils/errors'
import { formatTime } from '../utils/datetime'

const router = useRouter()
const route = useRoute()

// 模型清单与后端 feature_order.txt 的 [models] 段、utils/models.js 保持一致（8 种在线模型）
const models = MODELS

const filters = reactive({
  model_name: '',
  min_risk: null,
  page: 1,
  size: 20
})
const timeRange = ref([])
const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const retryable = ref(false)

// ── 已预测覆盖 + 补齐到最新（change startup-baseline-sync）──
const catching = ref(false)
const coverage = ref([])
const coverageText = computed(() => {
  if (!coverage.value.length) return ''
  const parts = coverage.value.map(
    (c) => `${c.model_name}: ${c.start ? c.start.slice(0, 10) : '—'} ~ ${c.end ? c.end.slice(0, 10) : '—'}`
  )
  return '已预测覆盖：' + parts.join('；')
})
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

// ── 按需现算（加载台）：空库时引导用户分批同步，绝不提前灌库 ──
const syncing = ref(false)
const syncCount = ref(10)
const syncPct = ref(0)
const syncMsg = ref('')

const hasFilter = computed(
  () =>
    !!(filters.model_name || filters.min_risk != null || (timeRange.value && timeRange.value.length))
)
const showBootstrap = computed(
  () => !loading.value && !error.value && !hasFilter.value && items.value.length === 0
)

// 分批触发 POST /api/sync：实测现算约 15s/条，一批 10 条控制在 3 分钟内（前端超时 300s）
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
    ElMessage.success(`同步完成，共 ${done} 条提交已现算并预测落库`)
    await load(1)
  } catch (e) {
    ElMessage.error(errText(e))
    syncMsg.value = `同步中断：${errText(e)}（已落库 ${done} 条，可再次点击继续）`
  } finally {
    syncing.value = false
  }
}

// 最新请求标识：并发时丢弃过期响应，避免快速翻页时旧响应覆盖新结果
// （2026-10-25 修复：此前 RiskList 无守卫，TrendBoard 有）
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
  filters.model_name = ''
  filters.min_risk = null
  timeRange.value = []
  load(1)
}

// 点击复制提交哈希（.stop 阻止冒泡，避免触发整行跳详情）
async function copyHash(hash) {
  try {
    await navigator.clipboard.writeText(hash)
    ElMessage.success('已复制提交哈希')
  } catch {
    ElMessage.error(`复制失败，请手动复制：${hash}`)
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
})

// 响应同路由 query 变化：query 变化重新查；query 移除清日期 + 重置分页
watch(() => route.query, applyQueryAndLoad)
</script>

<style scoped>
.filters {
  margin-bottom: 4px;
}
.boot {
  margin-bottom: 16px;
}
.boot h3 {
  margin: 0 0 10px;
}
.boot-desc {
  margin: 0 0 8px;
  color: #555;
  line-height: 1.6;
}
.boot-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 14px 0 10px;
}
.boot-progress {
  margin-bottom: 8px;
}
.sync-msg {
  margin: 0;
  color: #6b7280;
}
.mb {
  margin-bottom: 12px;
}
.risk-table {
  cursor: pointer;
}
.risk-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.risk-bar {
  width: 60px;
  height: 6px;
  border-radius: 3px;
  background: #eceef2;
  overflow: hidden;
  flex: 0 0 auto;
}
.risk-bar i {
  display: block;
  height: 100%;
  border-radius: 3px;
}
.risk-pct {
  font-family: monospace;
  font-weight: 600;
  min-width: 52px;
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
