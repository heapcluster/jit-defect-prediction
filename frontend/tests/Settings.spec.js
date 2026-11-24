import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { config, mount, flushPromises } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import * as store from '../src/utils/thresholds'

const api = vi.hoisted(() => ({ getConfig: vi.fn(), putConfig: vi.fn(), putConfigKey: vi.fn(), deleteConfigKey: vi.fn() }))
vi.mock('../src/api', () => api)
const views = import.meta.glob('../src/views/*.vue')
const Settings = views['../src/views/Settings.vue'] ? (await views['../src/views/Settings.vue']()).default : undefined
const fallbackLoading = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = fallbackLoading })

const metadata = {
  risk_high_threshold: { label: '高风险阈值', value_type: 'float', choices: null, group: 'global' },
  risk_mid_threshold: { label: '中风险阈值', value_type: 'float', choices: null, group: 'global' },
  page_prefs: { label: '页面偏好', value_type: 'object', choices: null, group: 'global' },
  effort_enabled: { label: '工作量指标', value_type: 'bool', choices: null, group: 'global' },
  default_model: { label: '默认模型', value_type: 'string', choices: ['', 'db_model_v3'], group: 'global' },
  default_xai: { label: '默认解释技术', value_type: 'string', choices: ['shap'], group: 'global' },
  metrics_selected: { label: '指标集合', value_type: 'list', choices: ['auc', 'f1'], group: 'global' },
  primary_metric: { label: '主指标', value_type: 'string', choices: ['auc', 'f1'], group: 'global' },
  'collect.allow_roots': { label: '允许路径', value_type: 'list', choices: null, group: 'collect' },
  'clean.chain_templates': { label: '清洗模板', value_type: 'object', choices: null, group: 'clean' },
  'train.templates': { label: '训练模板', value_type: 'object', choices: null, group: 'train' },
  'predict.batch_size': { label: '批大小', value_type: 'int', choices: null, group: 'predict' }
}
function fixture() {
  const values = {
    risk_high_threshold: 0.7, risk_mid_threshold: 0.3, page_prefs: {}, effort_enabled: true,
    default_model: '', default_xai: 'shap', metrics_selected: ['auc'], primary_metric: 'auc',
    'collect.allow_roots': ['/workspace'], 'clean.chain_templates': {}, 'train.templates': {}, 'predict.batch_size': 24
  }
  return {
    schema: structuredClone(metadata),
    items: Object.entries(values).map(([config_key, value]) => ({ config_key, value, value_type: metadata[config_key].value_type, source: 'factory', updated_at: null }))
  }
}
let server
let wrapper
beforeEach(() => {
  vi.resetAllMocks()
  server = fixture()
  api.getConfig.mockImplementation(async () => structuredClone(server))
  Object.assign(store.thresholds, { high: null, mid: null })
  if (store.configuration) Object.assign(store.configuration, { ready: false, loading: false, error: '', items: [], schema: {} })
})
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})
async function open() {
  expect(Settings, 'W1 configuration view must exist').toBeDefined()
  wrapper = mount(Settings, { attachTo: document.body, global: { plugins: [ElementPlus] } })
  await flushPromises()
  return wrapper
}
function field(key) { return wrapper.get(`[data-config-key="${key}"]`) }
async function save() {
  await wrapper.get('[data-testid="save-config"]').trigger('click')
  await flushPromises()
}
async function tab(group) {
  await wrapper.get(`[role="tab"][id$="-${group}"]`).trigger('click')
  await flushPromises()
}
function confirmBatch() {
  api.putConfig.mockImplementation(async (items) => {
    const effective = items.map(({ config_key, value }) => ({ ...server.items.find(item => item.config_key === config_key), value, source: 'global', updated_at: '2026-11-21T10:00:00Z' }))
    server.items = server.items.map(item => effective.find(saved => saved.config_key === item.config_key) || item)
    return { items: structuredClone(effective) }
  })
}

describe('W1 real Element Plus configuration form', () => {
  it('loads factory sources, metadata groups and valid JSON without W2 placeholders', async () => {
    await open()
    expect(wrapper.text()).toContain('用户配置')
    expect(field('risk_high_threshold').text()).toContain('factory')
    expect(field('risk_high_threshold').get('[data-testid="reset-config"]').attributes('disabled')).toBeDefined()
    expect(field('page_prefs').get('textarea').element.value).toBe('{}')
    expect(wrapper.findAll('[role="tab"]').length).toBe(5)
    expect(wrapper.text()).not.toContain('导入')
    expect(wrapper.text()).not.toContain('导出')
    expect(wrapper.text()).toContain('0 < risk_mid_threshold < risk_high_threshold < 1')
    expect(wrapper.text()).toContain('primary_metric')
    expect(wrapper.text()).toContain('不改写')
    const input = field('risk_high_threshold').get('input')
    expect(field('risk_high_threshold').get('label').attributes('for')).toBe(input.attributes('id'))
  })

  it('read failure is visible with retry, not an empty default form', async () => {
    api.getConfig.mockRejectedValueOnce(new Error('配置读取暂不可用'))
    await open()
    expect(wrapper.text()).toContain('配置读取暂不可用')
    expect(wrapper.find('[data-config-key]').exists()).toBe(false)
    expect(store.thresholds).toEqual({ high: null, mid: null })
    await wrapper.get('[data-testid="retry-config"]').trigger('click')
    await flushPromises()
    expect(field('risk_high_threshold').get('input').element.value).toBe('0.7')
  })

  it('no edits gives a tip and makes no PUT request', async () => {
    await open()
    await save()
    expect(api.putConfig).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('没有修改')
  })

  it('invalid JSON prevents the entire request and preserves the draft', async () => {
    await open()
    await field('page_prefs').get('textarea').setValue('{bad json')
    await field('risk_high_threshold').get('input').setValue('0.8')
    await save()
    expect(api.putConfig).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('JSON')
    expect(field('page_prefs').get('textarea').element.value).toBe('{bad json')
    expect(store.thresholds.high).toBe(0.7)
  })

  it('JSON type errors are rejected before save', async () => {
    await open()
    await field('page_prefs').get('textarea').setValue('[]')
    await save()
    expect(api.putConfig).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('对象')
  })

  it('one invalid backend field leaves the whole batch unsaved and drafts intact', async () => {
    await open()
    const error = Object.assign(new Error('请求参数有误'), { code: 40001, detail: 'page_prefs 含未知字段 invalid' })
    api.putConfig.mockRejectedValueOnce(error)
    await field('risk_high_threshold').get('input').setValue('0.8')
    await field('page_prefs').get('textarea').setValue('{"invalid":true}')
    await save()
    expect(api.putConfig).toHaveBeenCalledWith([
      { config_key: 'risk_high_threshold', value: 0.8 }, { config_key: 'page_prefs', value: { invalid: true } }
    ])
    expect(store.thresholds.high).toBe(0.7)
    expect(field('risk_high_threshold').text()).toContain('factory')
    expect(field('page_prefs').get('textarea').element.value).toBe('{"invalid":true}')
    expect(wrapper.text()).toContain(error.detail)
    expect(wrapper.text()).not.toContain('已保存')
  })

  it('saves only changed values, adopts confirmed thresholds and reloads sources', async () => {
    await open()
    confirmBatch()
    // Deliberately different confirmed value: the draft must never masquerade as a saved value.
    api.putConfig.mockImplementationOnce(async () => {
      const item = { ...server.items[0], value: 0.75, source: 'global' }
      server.items[0] = item
      return { items: [item] }
    })
    await field('risk_high_threshold').get('input').setValue('0.8')
    await save()
    expect(api.putConfig).toHaveBeenCalledWith([{ config_key: 'risk_high_threshold', value: 0.8 }])
    expect(store.thresholds.high).toBe(0.75)
    expect(field('risk_high_threshold').get('input').element.value).toBe('0.75')
    expect(field('risk_high_threshold').text()).toContain('global')
    expect(api.getConfig).toHaveBeenCalledTimes(2)
    await save()
    expect(api.putConfig).toHaveBeenCalledTimes(1)
  })

  it('a confirmed save survives a failed source reload with an explicit retry', async () => {
    await open()
    confirmBatch()
    api.getConfig.mockRejectedValueOnce(new Error('重新读取失败'))
    await field('risk_high_threshold').get('input').setValue('0.8')
    await save()
    expect(store.thresholds.high).toBe(0.8)
    expect(wrapper.text()).toContain('已保存')
    expect(wrapper.text()).toContain('重新读取失败')
    expect(field('risk_high_threshold').get('[data-testid="reset-config"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="retry-config"]').trigger('click')
    await flushPromises()
    expect(field('risk_high_threshold').text()).toContain('global')
  })

  it.each(['global', 'factory'])('single-key reset uses DELETE and the %s fallback, keeping other drafts', async (fallback) => {
    server.items[0].source = 'user'
    await open()
    await field('page_prefs').get('textarea').setValue('{"page_size":40}')
    api.deleteConfigKey.mockImplementationOnce(async (key) => {
      server.items[0] = { ...server.items[0], value: 0.6, source: fallback }
      return { config_key: key, deleted: true, fallback_source: fallback, value: 0.6 }
    })
    await field('risk_high_threshold').get('[data-testid="reset-config"]').trigger('click')
    await flushPromises()
    expect(api.deleteConfigKey).toHaveBeenCalledWith('risk_high_threshold')
    expect(api.putConfig).not.toHaveBeenCalled()
    expect(store.thresholds.high).toBe(0.6)
    expect(field('risk_high_threshold').text()).toContain(fallback)
    expect(field('page_prefs').get('textarea').element.value).toBe('{"page_size":40}')
    if (fallback === 'factory') expect(field('risk_high_threshold').get('[data-testid="reset-config"]').attributes('disabled')).toBeDefined()
  })

  it('DELETE errors retain the current source and draft', async () => {
    server.items[0].source = 'global'
    await open()
    api.deleteConfigKey.mockRejectedValueOnce(Object.assign(new Error('missing'), { code: 40400, detail: '当前作用域没有该配置' }))
    await field('risk_high_threshold').get('[data-testid="reset-config"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('当前作用域没有该配置')
    expect(store.thresholds.high).toBe(0.7)
    expect(field('risk_high_threshold').text()).toContain('global')
  })

  it('auth failure disables saving and resetting without discarding edits', async () => {
    server.items[0].source = 'global'
    await open()
    api.putConfig.mockRejectedValueOnce(Object.assign(new Error('auth'), { code: 40100, detail: 'API Token 无效' }))
    await field('risk_high_threshold').get('input').setValue('0.8')
    await save()
    expect(wrapper.get('[data-testid="save-config"]').attributes('disabled')).toBeDefined()
    expect(field('risk_high_threshold').get('[data-testid="reset-config"]').attributes('disabled')).toBeDefined()
    expect(field('risk_high_threshold').get('input').element.value).toBe('0.8')
    expect(wrapper.text()).toContain('API Token 无效')
  })

  it('real switches and server enum selects submit actual form changes', async () => {
    await open()
    confirmBatch()
    await field('effort_enabled').get('[role="switch"]').trigger('click')
    await field('default_model').get('.el-select').trigger('click')
    await flushPromises()
    const option = Array.from(document.querySelectorAll('[role="option"]')).find(node => node.textContent === 'db_model_v3')
    expect(option).toBeDefined()
    option.click()
    await flushPromises()
    await field('metrics_selected').get('.el-select').trigger('click')
    await flushPromises()
    Array.from(document.querySelectorAll('[role="option"]')).find(node => node.textContent === 'f1').click()
    await flushPromises()
    await save()
    expect(api.putConfig).toHaveBeenCalledWith([
      { config_key: 'effort_enabled', value: false }, { config_key: 'default_model', value: 'db_model_v3' },
      { config_key: 'metrics_selected', value: ['auc', 'f1'] }
    ])
    expect(document.body.textContent.toLowerCase()).not.toContain('lime')
  })

  it('generic non-enum lists are editable valid JSON', async () => {
    await open()
    await tab('collect')
    expect(JSON.parse(field('collect.allow_roots').get('textarea').element.value)).toEqual(['/workspace'])
    confirmBatch()
    await field('collect.allow_roots').get('textarea').setValue('["/next"]')
    await save()
    expect(api.putConfig).toHaveBeenCalledWith([{ config_key: 'collect.allow_roots', value: ['/next'] }])
  })

  it.each([['clean', 'clean.chain_templates'], ['train', 'train.templates']])('%s templates show the registry limitation and exact nonempty backend rejection', async (group, key) => {
    await open()
    await tab(group)
    expect(field(key).get('textarea').element.value).toBe('{}')
    expect(wrapper.text()).toContain('须等待对应操作/算法注册表实现')
    api.putConfig.mockRejectedValueOnce(Object.assign(new Error('invalid'), { code: 40001, detail: '非空模板须等待对应操作/算法注册表实现' }))
    await field(key).get('textarea').setValue('{"pipeline":[]}')
    await save()
    expect(wrapper.text()).toContain('非空模板须等待对应操作/算法注册表实现')
    expect(field(key).get('textarea').element.value).toBe('{"pipeline":[]}')
    confirmBatch()
    await field(key).get('textarea').setValue('{}')
    await save()
    expect(api.putConfig).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('没有修改')
  })

  it('saves an explicitly emptied template as {}, not a fabricated registered template', async () => {
    server.items.find(item => item.config_key === 'clean.chain_templates').value = { legacy: [] }
    await open()
    await tab('clean')
    confirmBatch()
    await field('clean.chain_templates').get('textarea').setValue('{}')
    await save()
    expect(api.putConfig).toHaveBeenCalledWith([{ config_key: 'clean.chain_templates', value: {} }])
  })

  it('does not render sensitive metadata keys or nested secret values', async () => {
    server.schema.api_key = { label: 'API Key', value_type: 'string', choices: null, group: 'global' }
    server.items.push({ config_key: 'api_key', value: 'must-not-appear', value_type: 'string', source: 'global' })
    server.items.find(item => item.config_key === 'page_prefs').value = { password: 'hidden-password' }
    await open()
    expect(wrapper.find('[data-config-key="api_key"]').exists()).toBe(false)
    expect(wrapper.html()).not.toContain('must-not-appear')
    expect(wrapper.html()).not.toContain('hidden-password')
  })
})
