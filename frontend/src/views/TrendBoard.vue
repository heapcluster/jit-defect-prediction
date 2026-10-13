<template>
  <div class="page">
    <el-form :inline="true" class="filters">
      <el-form-item label="粒度">
        <el-radio-group v-model="granularity">
          <el-radio-button value="week">按周</el-radio-button>
          <el-radio-button value="month">按月</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="模型">
        <el-select v-model="model_name" placeholder="全部模型" clearable style="width: 170px">
          <el-option v-for="m in MODEL_OPTIONS" :key="m" :label="m" :value="m" />
        </el-select>
      </el-form-item>
      <el-form-item label="时间范围">
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="起始"
          end-placeholder="截止"
          :value-format="DATETIME_FORMAT"
          style="width: 360px"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="load">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 汇总口径：提交总数与高风险数为求和；平均风险按 commit_count 加权（pages.md §4） -->
    <el-row :gutter="12" class="summary">
      <el-col :span="8">
        <el-statistic title="提交总数" :value="summary.total" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="高风险提交（≥0.5，后端口径）" :value="summary.high" />
      </el-col>
      <el-col :span="8">
        <el-statistic title="平均风险（按提交数加权）" :value="summary.avg" :precision="4" />
      </el-col>
    </el-row>

    <div v-loading="loading" ref="chartEl" class="chart" />

    <!-- 数据点 < 2 个：不画折线，只显明细表 + 提示（pages.md §4） -->
    <el-alert
      v-if="!loading && series.length > 0 && series.length < 2"
      type="info"
      :closable="false"
      title="数据点不足（少于 2 个），不画折线，仅显示明细表"
    />
    <el-alert
      v-if="!loading && series.length === 0"
      type="info"
      :closable="false"
      title="所选时间范围内没有数据"
    />

    <el-table v-if="series.length" :data="series" border size="small" class="detail-table">
      <el-table-column prop="period" label="周期" min-width="120" />
      <el-table-column prop="commit_count" label="提交数" min-width="100" align="right" />
      <el-table-column label="平均风险" min-width="110" align="right">
        <template #default="{ row }">
          <span class="risk" :class="riskClass(row.avg_risk)">{{ formatPct(row.avg_risk) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="high_risk_count" label="高风险数" min-width="110" align="right" />
    </el-table>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import { getTrends } from '../api'
import { handleError } from '../utils/feedback'
import { formatPct, riskClass } from '../utils/format'
import { MODEL_OPTIONS, DATETIME_FORMAT } from '../constants'

const granularity = ref('week')
const model_name = ref('')
const timeRange = ref(null)
const loading = ref(false)
const series = ref([])
const chartEl = ref(null)
let chart = null

const summary = computed(() => {
  const rows = series.value
  const total = rows.reduce((s, r) => s + (r.commit_count || 0), 0)
  const high = rows.reduce((s, r) => s + (r.high_risk_count || 0), 0)
  // 加权平均：Σ(avg_risk × commit_count) / Σcommit_count，非算术平均
  const weighted = rows.reduce((s, r) => s + (r.avg_risk || 0) * (r.commit_count || 0), 0)
  const avg = total > 0 ? weighted / total : 0
  return { total, high, avg: Number(avg.toFixed(4)) }
})

function buildParams() {
  const params = { granularity: granularity.value }
  if (model_name.value) params.model_name = model_name.value
  if (timeRange.value && timeRange.value.length === 2) {
    params.start_time = timeRange.value[0]
    params.end_time = timeRange.value[1]
  }
  return params
}

async function load() {
  loading.value = true
  try {
    const data = await getTrends(buildParams())
    series.value = (data && data.series) || []
  } catch (err) {
    handleError(err)
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (series.value.length < 2) {
    if (chart) {
      chart.clear()
    }
    return
  }
  if (!chart) chart = echarts.init(chartEl.value)
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      grid: { left: 56, right: 24, top: 24, bottom: 40 },
      xAxis: { type: 'category', boundaryGap: false, data: series.value.map((s) => s.period) },
      yAxis: { type: 'value', min: 0, max: 1, name: 'avg_risk' },
      series: [
        {
          name: '平均风险',
          type: 'line',
          smooth: true,
          showSymbol: true,
          areaStyle: { opacity: 0.15 },
          data: series.value.map((s) => s.avg_risk)
        }
      ]
    },
    true
  )
  chart.resize()
}

function onResize() {
  if (chart) chart.resize()
}

watch(series, renderChart)

onMounted(async () => {
  await load()
  renderChart()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filters {
  padding: 12px 12px 0;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}
.summary {
  margin-top: 4px;
}
.chart {
  height: 340px;
  width: 100%;
}
.detail-table {
  margin-top: 4px;
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
</style>
