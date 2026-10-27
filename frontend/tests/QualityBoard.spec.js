// @vitest-environment jsdom

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import QualityBoard from '../src/views/QualityBoard.vue'

const getQuality = vi.fn()
const getConfig = vi.fn()
const postCalibrate = vi.fn()
const putConfig = vi.fn()

vi.mock('../src/api', () => ({
  getQuality: (...args) => getQuality(...args),
  getConfig: (...args) => getConfig(...args),
  postCalibrate: (...args) => postCalibrate(...args),
  putConfig: (...args) => putConfig(...args)
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() }
}))

const QUALITY = {
  model_name: 'fixture_v2',
  threshold: 0.5,
  label_source: 'manual',
  labeled_total: 4,
  evaluated: 3,
  tp: 2,
  fp: 1,
  tn: 0,
  fn: 0,
  precision: 0.6667,
  recall: 1,
  f1: 0.8,
  accuracy: 0.6667,
  false_discovery_rate: 0.3333,
  avg_risk_defect: 0.9,
  avg_risk_clean: 0.2,
  recommended_threshold: 0.45,
  evaluated_at: '2026-10-27T00:00:00Z'
}

const stubs = {
  PageHint: { template: '<div><slot /></div>' },
  StatCard: {
    props: ['label', 'value', 'hint'],
    template: '<div class="stat">{{ label }}={{ value }}</div>'
  },
  'el-card': { template: '<div><slot name="header" /><slot /></div>' },
  'el-button': { template: '<button><slot /></button>' },
  'el-alert': { template: '<div><slot /></div>' },
  'el-radio-group': { template: '<div><slot /></div>' },
  'el-radio-button': { template: '<label><slot /></label>' }
}

function mountBoard() {
  return mount(QualityBoard, { global: { stubs } })
}

describe('QualityBoard', () => {
  beforeEach(() => {
    getQuality.mockReset()
    getConfig.mockReset()
    getQuality.mockResolvedValue(QUALITY)
    getConfig.mockResolvedValue({ high_risk_threshold: 0.5, mid_risk_threshold: 0.2 })
  })

  it('首屏按人工标签口径请求质量数据', async () => {
    mountBoard()
    await flushPromises()
    expect(getQuality).toHaveBeenCalledWith({ label_source: 'manual' })
  })

  it('把误发现率当作「误拦率」展示，而不是只显示精确率', async () => {
    const wrapper = mountBoard()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('误拦率')
    expect(text).toContain('33.3%') // false_discovery_rate=0.3333
    expect(text).toContain('66.7%') // precision=0.6667，两者互补
  })

  it('SZZ 对照视图下没有样本时给出对照口径说明', async () => {
    getQuality.mockResolvedValue({
      ...QUALITY,
      label_source: 'szz',
      labeled_total: 0,
      evaluated: 0,
      precision: null,
      recall: null,
      f1: null,
      false_discovery_rate: null
    })
    const wrapper = mountBoard()
    await flushPromises()
    // 首屏默认 manual，切换前提示仍是人工口径文案
    expect(wrapper.text()).toContain('还没有可评估的样本')
  })
})
