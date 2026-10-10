<template>
  <div>
    <h2>风险列表</h2>

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
        width="130"
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
            <span class="mono">{{ row.commit_hash.slice(0, 8) }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column
        prop="author_name"
        label="作者"
        width="110"
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

    <!-- 空数据：三态之一，不是错误 -->
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
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getCommits } from '../api'

const router = useRouter()
const route = useRoute()

// 模型清单前端维护（契约三冻结结论）
const models = ['xgb_v1', 'rf_v1', 'lr_v1']

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

// 风险阈值（docs/pages.md 第 5 节，只定义这一处）
function riskColor(score) {
  if (score >= 0.5) return '#d9484a'
  if (score >= 0.3) return '#d98a2b'
  return '#4e9b68'
}

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

// end_time 闭区间收尾：纯日期串补到当天 23:59:59，否则后端按 00:00:00 解析会丢最后一天
function toEndTime(dateStr) {
  if (!dateStr) return undefined
  return dateStr.includes('T') ? dateStr : dateStr + 'T23:59:59'
}

async function load(page = filters.page) {
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
      end_time: toEndTime(timeRange.value?.[1])
    })
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    items.value = []
    total.value = 0
    error.value = errText(e)
    retryable.value = e?.code === 50000
  } finally {
    loading.value = false
  }
}

// 错误码 → 提示（docs/pages.md 第 5 节）
function errText(e) {
  const code = e?.code
  // 40001 要指出是哪个参数，参数名在 err.detail
  if (code === 40001) return `参数有误：${e?.detail || e?.message || ''}`
  if (code === 40100) return '登录已失效，请重新登录'
  if (code === 40400) return '目标不存在'
  if (code === 50000) return '服务异常，请稍后重试'
  return e?.message || '请求失败'
}

function reset() {
  filters.model_name = ''
  filters.min_risk = null
  timeRange.value = []
  load(1)
}

function goDetail(row) {
  router.push(`/commit/${row.commit_hash}`)
}

onMounted(() => {
  // 从趋势看板点数据点跳转过来时，带上收窄的时间范围
  if (route.query.start_time && route.query.end_time) {
    timeRange.value = [route.query.start_time, route.query.end_time]
  }
  load(1)
})
</script>

<style scoped>
.filters {
  margin-bottom: 4px;
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
  min-width: 44px;
}
.mono {
  font-family: monospace;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
</style>
