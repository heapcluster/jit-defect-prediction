// AI-generated W5 tests, not human-reviewed.
import { afterAll, afterEach, beforeAll, beforeEach, expect, it, vi } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import { AxiosError } from 'axios'
import request from '../src/api/request'
import { configuration } from '../src/utils/thresholds'

const views = import.meta.glob('../src/views/*.vue')
const Train = views['../src/views/Train.vue'] ? (await views['../src/views/Train.vue']()).default : undefined
const algorithms = [
  { line: 'expert', algo: 'lr', family: '经典机器学习', enabled: true, description: '逻辑回归', input_requirements: 'Kamei14',
    hyperparams_schema: [{ name: 'lr__C', type: 'float', default: 1.0, min: 0.001, max: 100, choices: null, description: '正则强度倒数' }] },
  { line: 'expert', algo: 'rf', family: '经典机器学习', enabled: true, description: '随机森林', input_requirements: 'Kamei14',
    hyperparams_schema: [{ name: 'n_estimators', type: 'int', default: 300, min: 1, max: 2000, choices: null, description: '树数量' },
      { name: 'max_depth', type: 'int', default: null, min: 1, max: 100, choices: null, description: '最大深度（默认不限）' }] },
  { line: 'expert', algo: 'nb', family: '经典机器学习', enabled: false, description: '朴素贝叶斯（默认不训）', input_requirements: 'Kamei14', hyperparams_schema: [] }
]
const adapter = request.defaults.adapter, loading = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = loading })
let wrapper, calls, replies, job, fetchMock
function outputs() {
  return [{ name: 'train_lr_model_package_test-job.zip' }, { name: 'train_lr_model_package_test-job.manifest.json' },
    { name: 'train_metrics_test-job.csv' }, { name: 'train_comparison_test-job.json' },
    { name: 'train_roc_test-job.png' }, { name: 'train_pr_test-job.png' }, { name: 'train_confusion_test-job.png' },
    { name: 'train_metric_bars_test-job.png' }, { name: 'train_log_test-job.md' }]
}
beforeEach(async () => {
  calls = []; replies = {}
  configuration.items = [{ config_key: 'decision_threshold', value: 0.5 }, { config_key: 'primary_metric', value: 'auc' }]
  configuration.ready = true
  const sub = { algo: 'lr', model_name: 'lr_abcd1234_v1', version_key: 'abcd1234abcd1234', feature_version: 'v1', status: 'success',
    metrics: { auc: 0.9, f1: 0.8, precision: 0.8, recall: 0.8, accuracy: 0.8 }, hyperparams: { 'lr__C': 1.0 }, error: null }
  job = { job_id: 'test-job', kind: 'train', status: 'success', total: 2, done: 2, retry_count: 0,
    output_ref_json: { models: [sub], summary: { input_rows: 4, success_count: 1, failed_count: 0 }, outputs: outputs(), comparison_name: 'train_comparison_test-job.json' } }
  request.defaults.adapter = async cfg => {
    calls.push(cfg)
    const value = await (replies[cfg.url]?.shift() ?? (cfg.url === '/algorithms' ? { algorithms }
      : cfg.url === '/datasets' ? { items: [], total: 0 }
        : cfg.url === '/jobs' ? { items: [], total: 0 }
          : cfg.url === '/train/run' ? { job_id: job.job_id, status: job.status, models: job.output_ref_json.models }
            : cfg.url === '/train/compare' ? { primary_metric: 'auc', models: job.output_ref_json.models }
              : cfg.url.endsWith('/retry') ? { job_id: job.job_id, status: 'queued', retry_count: 1 }
                : cfg.url.endsWith('/cancel') ? { job_id: job.job_id, status: 'cancelled' }
                  : cfg.url === '/storage/import' ? { items: [{ status: 'success' }], summary: { inserted: 1, rejected: 0 } } : job))
    const response = { config: cfg, headers: {}, status: value?.code ? 400 : 200, data: value?.code ? value : { code: 0, data: value } }
    if (value?.code) throw new AxiosError('failed', 'ERR_BAD_RESPONSE', cfg, null, response)
    return response
  }
  fetchMock = vi.fn(async () => ({ ok: true, blob: async () => new Blob(['server file']) }))
  vi.stubGlobal('fetch', fetchMock)
  class TestURL extends URL {}
  Object.assign(TestURL, { createObjectURL: vi.fn(() => 'blob:train-test'), revokeObjectURL: vi.fn() })
  vi.stubGlobal('URL', TestURL)
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  const stores = import.meta.glob('../src/utils/train.js')
  if (stores['../src/utils/train.js']) Object.assign((await stores['../src/utils/train.js']()).training, { job: null, request: null })
})
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = ''; request.defaults.adapter = adapter; vi.restoreAllMocks(); vi.unstubAllGlobals() })
async function open() {
  expect(Train, 'real train view must exist').toBeDefined()
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/train', component: Train }] })
  await router.push('/train'); await router.isReady()
  wrapper = mount(Train, { attachTo: document.body, global: { plugins: [ElementPlus, router] } }); await flushPromises()
}
async function upload() {
  const input = wrapper.get('#train-files')
  Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['table'], 'cleaned.csv'), new File(['{}'], 'cleaned.manifest.json')] })
  await input.trigger('change')
}
async function click(id) { await wrapper.get(`[data-testid="${id}"]`).trigger('click'); await flushPromises() }
const last = url => calls.filter(call => call.url === url).at(-1)

it('wires real train route', async () => {
  expect(Train).toBeDefined()
  const router = (await import('../src/router')).default
  expect(router.options.routes.find(route => route.path === '/train')?.component).toBe(Train)
})
it('loads algorithms per line and renders schema-driven hyperparams', async () => {
  await open()
  expect(wrapper.findAll('[data-testid="train-algo"]')).toHaveLength(3)
  await wrapper.get('#train-algo-lr').setValue(true)
  expect(wrapper.get('#train-hp-lr-lr__C').element.value).toBe('1')
  expect(last('/algorithms').params.line).toBe('expert')
})
it('runs with uploaded file plus manifest and no automatic import', async () => {
  await open(); await upload(); await wrapper.get('#train-algo-lr').setValue(true); await click('train-run')
  expect(last('/train/run').data.getAll('files[]').map(f => f.name)).toEqual(['cleaned.csv', 'cleaned.manifest.json'])
  expect(JSON.parse(last('/train/run').data.get('config')).algos).toEqual(['lr'])
  expect(last('/storage/import')).toBeUndefined()
})
it('retains draft when no file and disables run without algorithms', async () => {
  await open(); await click('train-run')
  expect(last('/train/run')).toBeUndefined()
  expect(wrapper.text()).toContain('上传')
  expect(wrapper.get('[data-testid="train-run"]').attributes('disabled')).toBeDefined()
})
it('blocks non-expert line with input-requirements reason', async () => {
  await open(); await upload(); await wrapper.get('#train-line').setValue('semantic')
  expect(wrapper.text()).toContain('可读仓库')
  expect(wrapper.get('[data-testid="train-run"]').attributes('disabled')).toBeDefined()
})
it('submits hyperparameter overrides and split ratio', async () => {
  await open(); await upload(); await wrapper.get('#train-algo-lr').setValue(true)
  await wrapper.get('#train-hp-lr-lr__C').setValue(2.5)
  await wrapper.get('#train-ratio').setValue(0.8)
  await click('train-run')
  const sent = JSON.parse(last('/train/run').data.get('config'))
  expect(sent.hyperparams.lr['lr__C']).toBe(2.5)
  expect(sent.split.ratio).toBe(0.8)
})
it('omits null hyperparameter defaults so backend keeps constructor defaults', async () => {
  await open(); await upload(); await wrapper.get('#train-algo-rf').setValue(true); await click('train-run')
  const sent = JSON.parse(last('/train/run').data.get('config'))
  expect(sent.hyperparams.rf.n_estimators).toBe(300)
  expect(sent.hyperparams.rf).not.toHaveProperty('max_depth')
})
it('renders comparison sorted by primary metric and authenticated figures', async () => {
  await open(); await upload(); await wrapper.get('#train-algo-lr').setValue(true); await click('train-run')
  expect(wrapper.get('[data-testid="train-comparison"]').text()).toContain('lr_abcd1234_v1')
  expect(wrapper.findAll('.charts img')).toHaveLength(4)
  expect(fetchMock.mock.calls.every(([, o]) => 'X-API-Key' in o.headers)).toBe(true)
})
it('imports model package only after explicit action', async () => {
  await open(); await upload(); await wrapper.get('#train-algo-lr').setValue(true); await click('train-run')
  expect(last('/storage/import')).toBeUndefined()
  await click('train-import')
  expect(last('/storage/import').data.getAll('files[]').map(f => f.name)).toEqual(['train_lr_model_package_test-job.zip'])
})
it('downloads package and releases figure URLs on unmount', async () => {
  await open(); await upload(); await wrapper.get('#train-algo-lr').setValue(true); await click('train-run')
  await click('train-download-train_lr_model_package_test-job.zip')
  expect(fetchMock.mock.calls.some(([u]) => u.endsWith('.zip'))).toBe(true)
  wrapper.unmount(); wrapper = null
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:train-test')
})
it('keeps draft on backend validation error', async () => {
  replies['/train/run'] = [{ code: 40001, message: '超参越界' }]
  await open(); await upload(); await wrapper.get('#train-algo-lr').setValue(true); await click('train-run')
  expect(wrapper.text()).toContain('超参越界')
  expect(wrapper.text()).toContain('cleaned.csv')
})
it('retries original job and cancels running job', async () => {
  job.status = 'failed'; job.error_log = 'boom'
  await open(); await upload(); await wrapper.get('#train-algo-lr').setValue(true); await click('train-run'); await click('train-retry')
  expect(last('/jobs/test-job/retry')).toBeDefined()
  expect(calls.filter(c => c.url === '/train/run')).toHaveLength(1)
  job.status = 'running'
  await click('train-run'); await click('train-cancel')
  expect(last('/jobs/test-job/cancel')).toBeDefined()
})
it('saves and restores a training template without launching a job', async () => {
  await open(); await wrapper.get('#train-algo-lr').setValue(true)
  await wrapper.get('#train-template-name').setValue('exp'); await click('train-save-template')
  expect(JSON.parse(last('/config/train.templates').data).value.exp.algos).toEqual(['lr'])
  expect(last('/train/run')).toBeUndefined()
})
