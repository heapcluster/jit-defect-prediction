<template>
  <div
    ref="chartEl"
    :style="{ width: '100%', height }"
  />
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  // series[]: { period, commit_count, avg_risk, high_risk_count }
  series: { type: Array, default: () => [] },
  height: { type: String, default: '360px' },
  // 图表类型：line 折线 / bar 柱状
  chartType: { type: String, default: 'line' }
})

const emit = defineEmits(['point-click'])

// 提交数与高风险数量级相差大：双 Y 轴（左提交数、右高风险数）才能在同一图里比对
const SERIES_DEFS = [
  { key: 'commit_count', name: '提交数', color: '#3b5bdb', axis: 0 },
  { key: 'high_risk_count', name: '高风险数', color: '#d9484a', axis: 1 }
]

const chartEl = ref(null)
let chart = null
let resizeObserver = null

function render() {
  if (!chart) return
  const isBar = props.chartType === 'bar'

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const idx = params[0]?.dataIndex
        const s = props.series[idx]
        if (!s) return ''
        const rows = params.map((p) => `${p.marker}${p.seriesName}：${p.value}`)
        return [s.period, ...rows].join('<br/>')
      }
    },
    legend: { data: SERIES_DEFS.map((d) => d.name), top: 0 },
    grid: { left: 56, right: 56, top: 36, bottom: 32 },
    xAxis: {
      type: 'category',
      data: props.series.map((s) => s.period),
      axisLabel: { color: '#7c838c' },
      axisLine: { lineStyle: { color: '#cbd2dc' } }
    },
    yAxis: [
      {
        type: 'value',
        name: '提交数',
        min: 0,
        axisLabel: { color: '#7c838c' },
        splitLine: { lineStyle: { color: '#eceef2' } }
      },
      {
        type: 'value',
        name: '高风险数',
        min: 0,
        axisLabel: { color: '#7c838c' },
        splitLine: { show: false }
      }
    ],
    series: SERIES_DEFS.map((d) => {
      if (isBar) {
        return {
          name: d.name,
          type: 'bar',
          yAxisIndex: d.axis,
          data: props.series.map((s) => s[d.key]),
          itemStyle: { color: d.color },
          barMaxWidth: 28
        }
      }
      return {
        name: d.name,
        type: 'line',
        yAxisIndex: d.axis,
        data: props.series.map((s) => s[d.key]),
        itemStyle: { color: d.color },
        lineStyle: { width: 2 },
        symbol: 'circle',
        symbolSize: 6
      }
    })
    // notMerge：数据点变少时清掉上一轮的残留点，否则图形会「只增不减」
  }, { notMerge: true })
}

watch(() => [props.series, props.chartType], render, { deep: true })

function onResize() {
  chart?.resize()
}

onMounted(() => {
  chart = echarts.init(chartEl.value)
  render()
  // 点击数据点 → 跳转风险列表（docs/web_page/trend_board.md）
  chart.on('click', (params) => {
    const s = props.series[params.dataIndex]
    if (s) emit('point-click', s)
  })
  window.addEventListener('resize', onResize)
  if (typeof ResizeObserver !== 'undefined' && chartEl.value) {
    resizeObserver = new ResizeObserver(() => chart?.resize())
    resizeObserver.observe(chartEl.value)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  resizeObserver?.disconnect()
  resizeObserver = null
  chart?.dispose()
})
</script>
