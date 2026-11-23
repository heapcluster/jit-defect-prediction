// AI-generated W7 tests, not human-reviewed.
import { afterAll, afterEach, beforeAll, beforeEach, expect, it, vi } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import { AxiosError } from 'axios'
import request from '../src/api/request'
import { configuration } from '../src/utils/thresholds'

const views = import.meta.glob('../src/views/*.vue')
const Evaluate = views['../src/views/Evaluate.vue'] ? (await views['../src/views/Evaluate.vue']()).default : undefined
const registry = ['auc', 'ap', 'f1', 'precision', 'recall', 'accuracy', 'recall_at_20', 'recall_at_50', 'p_norm', 'popt'].map(key => ({ key, name: key, effort_aware: key.includes('recall_at') || key === 'p_norm' || key === 'popt' }))
const adapter = request.defaults.adapter, loading = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = loading })
let wrapper, calls, replies, job, fetchMock
function outputs() {
  return [{ name: 'evaluate_metrics_test-job.csv' }, { name: 'evaluate_confusion_test-job.csv' },
    { name: 'evaluate_comparison_test-job.json' }, { name: 'evaluate_report_test-job.md' },
    { name: 'evaluate_roc_test-job.png' }, { name: 'evaluate_effort_aware_test-job.png' }]
}
beforeEach(async () => {
  calls = []; replies = {}
  configuration.items = [{ config_key: 'decision_threshold', value: 0.5 }]; configuration.ready = true
  job = { job_id: 'test-job', kind: 'evaluate', status: 'success', total: 2, done: 2, retry_count: 0,
    output_ref_json: { outputs: outputs(), summary: { rows: 16, primary_metric: 'auc', threshold: 0.5, label_stats: { conflicts: 0, unlabeled: 0 } } } }
  request.defaults.adapter = async cfg => {
    calls.push(cfg)
    const value = await (replies[cfg.url]?.shift() ?? (cfg.url === '/evaluate/metrics' ? { metrics: registry, defaults: { metrics_selected: ['auc', 'f1'], primary_metric: 'auc', effort_enabled: true } }
      : cfg.url === '/jobs' ? { items: [], total: 0 }
        : cfg.url === '/evaluate/run' ? { job_id: job.job_id, status: job.status }
          : cfg.url.endsWith('/retry') ? { job_id: job.job_id, status: 'queued', retry_count: 1 }
            : cfg.url.endsWith('/cancel') ? { job_id: job.job_id, status: 'cancelled' } : job))
    const response = { config: cfg, headers: {}, status: value?.code ? 400 : 200, data: value?.code ? value : { code: 0, data: value } }
    if (value?.code) throw new AxiosError('failed', 'ERR_BAD_RESPONSE', cfg, null, response)
    return response
  }
  fetchMock = vi.fn(async (url) => ({ ok: true, blob: async () => new Blob([url.endsWith('comparison_test-job.json') ? JSON.stringify({ models: [{ model_name: 'm1', metrics: { auc: 0.9, f1: 0.8 }, n: 8, pos_rate: 0.5, status: 'ok' }], unavailable: [{ model_name: 'm2', reason_code: 'missing_effort', message: '缺 LOC' }] }) : 'file']) }))
  vi.stubGlobal('fetch', fetchMock)
  class TestURL extends URL {}
  Object.assign(TestURL, { createObjectURL: vi.fn(() => 'blob:eval-test'), revokeObjectURL: vi.fn() })
  vi.stubGlobal('URL', TestURL)
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  const stores = import.meta.glob('../src/utils/evaluate.js')
  if (stores['../src/utils/evaluate.js']) Object.assign((await stores['../src/utils/evaluate.js']()).evaluating, { job: null })
})
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = ''; request.defaults.adapter = adapter; vi.restoreAllMocks(); vi.unstubAllGlobals() })
async function open() {
  expect(Evaluate, 'real evaluate view must exist').toBeDefined()
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/evaluate', component: Evaluate }] })
  await router.push('/evaluate'); await router.isReady()
  wrapper = mount(Evaluate, { attachTo: document.body, global: { plugins: [ElementPlus, router] } }); await flushPromises()
}
async function upload() {
  const input = wrapper.get('#eval-files')
  Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['p'], 'predictions.csv')] })
  await input.trigger('change')
}
async function click(id) { await wrapper.get(`[data-testid="${id}"]`).trigger('click'); await flushPromises() }
const last = url => calls.filter(call => call.url === url).at(-1)

it('wires real evaluate route and renders registry', async () => {
  expect(Evaluate).toBeDefined()
  const router = (await import('../src/router')).default
  expect(router.options.routes.find(route => route.path === '/evaluate')?.component).toBe((await import('../src/views/EvaluateWorkbench.vue')).default)
  await open()
  expect(wrapper.findAll('.metric-select input')).toHaveLength(10)
})
it('runs with predictions file and submits config', async () => {
  await open(); await upload(); await click('eval-run')
  expect(last('/evaluate/run').data.getAll('files[]').map(f => f.name)).toEqual(['predictions.csv'])
  const sent = JSON.parse(last('/evaluate/run').data.get('config'))
  expect(sent.metrics).toContain('auc')
  expect(sent.primary_metric).toBe('auc')
})
it('disables run without file', async () => {
  await open()
  expect(wrapper.get('[data-testid="eval-run"]').attributes('disabled')).toBeDefined()
})
it('renders comparison, unavailable reasons and authenticated figures', async () => {
  await open(); await upload(); await click('eval-run')
  expect(wrapper.get('[data-testid="eval-comparison"]').text()).toContain('m1')
  expect(wrapper.text()).toContain('missing_effort')
  expect(wrapper.findAll('.charts img')).toHaveLength(2)
  expect(fetchMock.mock.calls.every(([, o]) => 'X-API-Key' in o.headers)).toBe(true)
})
it('downloads report and retries original job', async () => {
  await open(); await upload(); await click('eval-run')
  await click('eval-download-evaluate_report_test-job.md')
  expect(fetchMock.mock.calls.some(([u]) => u.endsWith('.md'))).toBe(true)
  job.status = 'failed'; job.error_log = 'boom'
  await click('eval-run'); await click('eval-retry')
  expect(last('/jobs/test-job/retry')).toBeDefined()
})
it('keeps draft on backend error', async () => {
  replies['/evaluate/run'] = [{ code: 40001, message: '阈值越界' }]
  await open(); await upload(); await click('eval-run')
  expect(wrapper.text()).toContain('阈值越界')
  expect(wrapper.text()).toContain('predictions.csv')
})
