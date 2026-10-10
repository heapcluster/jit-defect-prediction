<template>
  <div>
    <h2>缺陷引入趋势看板</h2>

    <!-- 筛选栏 -->
    <el-form
      :inline="true"
      class="filters"
    >
      <el-form-item label="粒度">
        <el-radio-group v-model="filters.granularity">
          <el-radio-button value="week">
            周
          </el-radio-button>
          <el-radio-button value="month">
            月
          </el-radio-button>
        </el-radio-group>
      </el-form-item>
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
          @click="load"
        >
          查询
        </el-button>
      </el-form-item>
    </el-form>

    <!-- 请求失败 -->
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
        @click="load"
      >
        重试
      </el-button>
    </el-alert>

    <!-- 汇总卡片 -->
    <div
      v-if="summary"
      class="cards"
    >
      <div class="stat">
        <div class="k">
          区间内提交总数
        </div>
        <div class="v">
          {{ summary.commit_count }}
        </div>
      </div>
      <div class="stat">
        <div class="k">
          高风险提交
        </div>
        <div class="v">
          {{ summary.high_risk_count }}
        </div>
      </div>
      <div class="stat">
        <div class="k">
          加权平均风险
        </div>
        <div class="v">
          {{ summary.avg_risk }}
        </div>
      </div>
    </div>

    <!-- 折线图：容器始终渲染保持高度稳定（pages.md §5） -->
    <div
      v-loading="loading"
      class="chart-box"
    >
      <RiskTrendChart
        v-if="series.length >= 2"
        :series="series"
        @point-click="onPointClick"
      />
      <div
        v-else-if="!error"
        class="chart-placeholder"
      >
        <p>
          {{ series.length === 0 ? '所选时间范围内没有数据' : '数据点不足，无法绘制趋势' }}
        </p>
        <el-button
          v-if="series.length === 0"
          size="small"
          @click="resetRange"
        >
          重置时间范围
        </el-button>
      </div>
    </div>

    <!-- 明细表 -->
    <el-table
      v-if="series.length > 0"
      :data="series"
      class="detail-table"
    >
      <el-table-column
        prop="period"
        label="周期"
        class-name="mono-col"
      />
      <el-table-column
        prop="commit_count"
        label="提交数"
        width="110"
      />
      <el-table-column
        prop="high_risk_count"
        label="高风险数"
        width="110"
      />
      <el-table-column
        label="平均风险"
        width="110"
      >
        <template #default="{ row }">
          {{ row.avg_risk }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTrends } from '../api'
import RiskTrendChart from '../components/RiskTrendChart.vue'

// 模型清单前端维护（契约三冻结结论）
const models = ['xgb_v1', 'rf_v1', 'lr_v1']

const filters = reactive({
  granularity: 'week',
  model_name: ''
})
const timeRange = ref([])
const series = ref([])
const loading = ref(false)
const error = ref('')
const retryable = ref(false)

// 汇总：提交总数、高风险数求和，平均风险按 commit_count 加权
const summary = computed(() => {
  if (!series.value.length) return null
  const commitCount = series.value.reduce((s, x) => s + x.commit_count, 0)
  const highRiskCount = series.value.reduce((s, x) => s + x.high_risk_count, 0)
  const weighted = series.value.reduce(
    (s, x) => s + x.avg_risk * x.commit_count,
    0
  )
  const avgRisk = commitCount > 0 ? weighted / commitCount : 0
  return {
    commit_count: commitCount,
    high_risk_count: highRiskCount,
    avg_risk: avgRisk.toFixed(2)
  }
})

async function load() {
  loading.value = true
  error.value = ''
  retryable.value = false
  try {
    const data = await getTrends({
      granularity: filters.granularity,
      model_name: filters.model_name || undefined,
      start_time: timeRange.value?.[0] || undefined,
      end_time: timeRange.value?.[1] || undefined
    })
    series.value = data.series || []
  } catch (e) {
    series.value = []
    error.value = errText(e)
    retryable.value = e?.code === 50000
  } finally {
    loading.value = false
  }
}

function errText(e) {
  const code = e?.code
  // 40001 要指出是哪个参数，参数名在 err.detail
  if (code === 40001) return `参数有误：${e?.detail || e?.message || ''}`
  if (code === 40100) return '登录已失效，请重新登录'
  if (code === 50000) return '服务异常，请稍后重试'
  return e?.message || '请求失败'
}

const router = useRouter()

// 点击数据点 → 跳风险列表，时间范围收窄到该周期（docs/pages.md §4）
function onPointClick(s) {
  const range = periodToRange(s.period, filters.granularity)
  if (range.length) {
    router.push({ path: '/', query: { start_time: range[0], end_time: range[1] } })
  }
}

function periodToRange(period, granularity) {
  if (granularity === 'week') {
    // "2026-W30" → 该 ISO 周的周一~周日
    const m = period.match(/^(\d{4})-W(\d{1,2})$/)
    if (!m) return []
    const year = Number(m[1])
    const week = Number(m[2])
    const jan1 = new Date(Date.UTC(year, 0, 1))
    const dow = (jan1.getUTCDay() + 6) % 7
    const monday = new Date(Date.UTC(year, 0, 1 + (week - 1) * 7 - dow))
    return [toDateStr(monday), toDateStr(new Date(monday.getTime() + 6 * 86400000))]
  }
  // "2026-08" → 该月 1 日~月末
  const m = period.match(/^(\d{4})-(\d{1,2})$/)
  if (!m) return []
  const year = Number(m[1])
  const month = Number(m[2])
  return [
    toDateStr(new Date(Date.UTC(year, month - 1, 1))),
    toDateStr(new Date(Date.UTC(year, month, 1)))
  ]
}

function toDateStr(d) {
  return d.toISOString().slice(0, 10)
}

function resetRange() {
  timeRange.value = []
  load()
}

onMounted(load)
</script>

<style scoped>
.filters {
  margin-bottom: 4px;
}
.mb {
  margin-bottom: 12px;
}
.cards {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.stat {
  flex: 1;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  padding: 12px 16px;
}
.stat .k {
  font-size: 12px;
  color: #7c838c;
}
.stat .v {
  font-size: 26px;
  font-weight: 700;
  font-family: monospace;
  margin-top: 2px;
}
.chart-box {
  border: 1px solid #e2e5ea;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}
.chart-placeholder {
  height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #7c838c;
}
.chart-placeholder p {
  margin: 0 0 12px;
}
.detail-table {
  margin-top: 4px;
}
:deep(.mono-col) {
  font-family: monospace;
}
</style>
