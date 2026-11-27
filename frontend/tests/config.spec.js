import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h, isReactive } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import * as store from '../src/utils/thresholds'
import { riskLabel } from '../src/utils/risk'
import App from '../src/App.vue'

const boundary = vi.hoisted(() => ({ getConfig: vi.fn(), putConfig: vi.fn(), putConfigKey: vi.fn(), deleteConfigKey: vi.fn() }))
vi.mock('../src/api', async importOriginal => ({ ...(await importOriginal()), ...boundary }))

const response = () => ({
  items: [
    { config_key: 'risk_high_threshold', value: 0.7, value_type: 'float', source: 'factory', updated_at: null },
    { config_key: 'risk_mid_threshold', value: 0.3, value_type: 'float', source: 'global', updated_at: null }
  ],
  schema: {
    risk_high_threshold: { label: '高风险阈值', value_type: 'float', choices: null, group: 'global' },
    risk_mid_threshold: { label: '中风险阈值', value_type: 'float', choices: null, group: 'global' }
  }
})
const initialThresholds = { ...store.thresholds }
const fallbackLoading = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = fallbackLoading })
const RiskProbe = defineComponent({ setup: () => () => h('div', { 'data-testid': 'business' }, riskLabel(0.6)) })
let wrapper
beforeEach(() => {
  vi.clearAllMocks()
  boundary.getConfig.mockReset().mockResolvedValue(response())
  Object.assign(store.thresholds, { high: null, mid: null })
  if (store.configuration) Object.assign(store.configuration, { ready: false, loading: false, error: '', items: [], schema: {} })
})
afterEach(() => wrapper?.unmount())

function requireStore() {
  expect(store.loadConfiguration, 'configuration loader is required').toBeTypeOf('function')
  expect(store.applyConfiguration, 'server-confirmed configuration application is required').toBeTypeOf('function')
}

describe('server-backed reactive configuration', () => {
  it('starts unloaded, without manufactured threshold defaults', () => {
    expect(initialThresholds).toEqual({ high: null, mid: null })
    expect(store.thresholds).toEqual({ high: null, mid: null })
    expect(isReactive(store.thresholds)).toBe(true)
  })

  it('loads effective backend values and sources', async () => {
    requireStore()
    await store.loadConfiguration()
    expect(boundary.getConfig).toHaveBeenCalledWith()
    expect(store.configuration.ready).toBe(true)
    expect(store.thresholds).toEqual({ high: 0.7, mid: 0.3 })
    expect(store.configuration.items[1].source).toBe('global')
  })

  it('failed initial read remains unloaded and supports retry', async () => {
    requireStore()
    boundary.getConfig.mockRejectedValueOnce(new Error('配置读取失败'))
    await expect(store.loadConfiguration()).rejects.toThrow('配置读取失败')
    expect(store.configuration.ready).toBe(false)
    expect(store.configuration.error).toContain('配置读取失败')
    expect(store.thresholds).toEqual({ high: null, mid: null })
    await store.loadConfiguration()
    expect(store.configuration.ready).toBe(true)
    expect(store.configuration.error).toBe('')
  })

  it('incomplete reads do not unlock business views', async () => {
    requireStore()
    boundary.getConfig.mockResolvedValue({ items: [], schema: {} })
    await expect(store.loadConfiguration()).rejects.toThrow()
    expect(store.configuration.ready).toBe(false)
    expect(store.thresholds).toEqual({ high: null, mid: null })
  })

  it('confirmed partial updates re-render real risk formulas without rescoring data', async () => {
    requireStore()
    await store.loadConfiguration()
    const score = 0.6
    wrapper = mount(RiskProbe)
    expect(wrapper.text()).toBe('中等风险')
    await store.applyConfiguration({ items: [{ ...response().items[0], value: 0.55, source: 'global' }] })
    await flushPromises()
    expect(store.thresholds.mid).toBe(0.3)
    expect(wrapper.text()).toBe('高风险')
    expect(score).toBe(0.6)
  })

  it('later read failure retains the last confirmed values', async () => {
    requireStore()
    await store.loadConfiguration()
    boundary.getConfig.mockRejectedValueOnce(new Error('网络中断'))
    await expect(store.loadConfiguration()).rejects.toThrow('网络中断')
    expect(store.configuration.ready).toBe(true)
    expect(store.thresholds).toEqual({ high: 0.7, mid: 0.3 })
  })
})

describe('configuration boot gate and navigation', () => {
  it('blocks real router-view on read failure, then retries and keeps navigation', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: RiskProbe }, { path: '/storage', component: RiskProbe }] })
    await router.push('/')
    await router.isReady()
    boundary.getConfig.mockRejectedValueOnce(new Error('配置服务不可用'))
    wrapper = mount(App, { global: { plugins: [ElementPlus, router] } })
    await flushPromises()
    expect(wrapper.find('[data-testid="business"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('配置服务不可用')
    const retry = wrapper.findAll('button').find(button => button.text() === '重试')
    expect(retry).toBeDefined()
    await retry.trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="business"]').text()).toBe('中等风险')
    await router.push('/storage')
    await flushPromises()
    expect(wrapper.findAll('.menu [role="menuitem"]').map(item => item.text())).toEqual([
      '数据存储', '数据收集', '数据清洗', '模型训练', '模型预测', '预测评估', '系统设置'
    ])
  })

  it('registers storage and settings as real top-level views', async () => {
    const module = await import('../src/router/index.js')
    const routes = module.default.options.routes
    expect(routes.find(route => route.path === '/storage')?.component.__file).toContain('Storage.vue')
    expect(routes.find(route => route.path === '/settings')?.component.__file).toContain('Settings.vue')
  })
})

describe('configuration HTTP contract', () => {
  it('maps optional keys, atomic batch, single PUT and DELETE to config endpoints', async () => {
    const api = await vi.importActual('../src/api/index.js')
    const { default: request } = await import('../src/api/request.js')
    const get = vi.spyOn(request, 'get').mockResolvedValue(response())
    const put = vi.spyOn(request, 'put').mockResolvedValue({ items: [] })
    const del = vi.spyOn(request, 'delete').mockResolvedValue({ deleted: true })
    try {
      expect(api.getConfig).toBeTypeOf('function')
      expect(api.putConfig).toBeTypeOf('function')
      expect(api.putConfigKey).toBeTypeOf('function')
      expect(api.deleteConfigKey).toBeTypeOf('function')
      await api.getConfig(['risk_high_threshold', 'risk_mid_threshold'])
      expect(get).toHaveBeenCalledWith('/config', { params: { keys: 'risk_high_threshold,risk_mid_threshold' } })
      const items = [{ config_key: 'risk_high_threshold', value: 0.7 }]
      await api.putConfig(items)
      expect(put).toHaveBeenCalledWith('/config', { items })
      await api.putConfigKey('page_prefs', {})
      expect(put).toHaveBeenCalledWith('/config/page_prefs', { value: {} })
      await api.deleteConfigKey('page_prefs')
      expect(del).toHaveBeenCalledWith('/config/page_prefs')
    } finally {
      get.mockRestore()
      put.mockRestore()
      del.mockRestore()
    }
  })
})
