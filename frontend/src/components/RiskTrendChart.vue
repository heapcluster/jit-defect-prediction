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
  height: { type: String, default: '320px' }
})

const emit = defineEmits(['point-click'])

const chartEl = ref(null)
let chart = null
// 容器尺寸变化（侧边栏折叠、窗口缩放）时 ECharts 不会自动重绘，
// 只监听 window.resize 会漏掉布局变化 → 用 ResizeObserver 兜住（2026-10-25 修复）
let resizeObserver = null

function render() {
  if (!chart) return
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const idx = params[0]?.dataIndex
        const s = props.series[idx]
        if (!s) return ''
        return [
          `${s.period}`,
          `提交数：${s.commit_count}`,
          `高风险：${s.high_risk_count}`,
          `平均风险：${s.avg_risk}`
        ].join('<br/>')
      }
    },
    grid: { left: 48, right: 20, top: 24, bottom: 32 },
    xAxis: {
      type: 'category',
      data: props.series.map((s) => s.period),
      axisLabel: { color: '#7c838c' },
      axisLine: { lineStyle: { color: '#cbd2dc' } }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLabel: { color: '#7c838c' },
      splitLine: { lineStyle: { color: '#eceef2' } }
    },
    series: [
      {
        type: 'line',
        data: props.series.map((s) => s.avg_risk),
        lineStyle: { color: '#3b5bdb', width: 2 },
        itemStyle: { color: '#3b5bdb' },
        areaStyle: { color: '#3b5bdb', opacity: 0.08 }
      }
    ]
  })
}

watch(() => props.series, render, { deep: true })

function onResize() {
  chart?.resize()
}

onMounted(() => {
  chart = echarts.init(chartEl.value)
  render()
  // 点击数据点 → 跳转风险列表（docs/pages.md §4）
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
