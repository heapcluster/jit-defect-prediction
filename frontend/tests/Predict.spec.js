// AI-generated W6 tests, not human-reviewed.
import { afterAll, afterEach, beforeAll, beforeEach, expect, it, vi } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import { AxiosError } from 'axios'
import request from '../src/api/request'
import { configuration } from '../src/utils/thresholds'

const views = import.meta.glob('../src/views/*.vue')
const Predict = views['../src/views/Predict.vue'] ? (await views['../src/views/Predict.vue']()).default : undefined
const adapter = request.defaults.adapter, loading = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = loading })
let wrapper, calls, replies, job, fetchMock
const csvText = 'commit_hash,model_name,risk_score,predicted_label,decision_threshold,model_version,feature_version,predicted_at,is_bug_inducing\n'
  + 'a'.repeat(40) + ',lr_v1,0.83000,1,0.5,v1,v1,2026-01-01T00:00:00Z,1\n'
  + 'b'.repeat(40) + ',lr_v1,0.12000,0,0.5,v1,v1,2026-01-01T00:00:00Z,\n'
function outputs() {
  return [{ name: 'predict_predictions_test-job.csv' }, { name: 'predict_predictions_test-job.xlsx' },
    { name: 'predict_predictions_test-job.manifest.json' }, { name: 'predict_summary_test-job.json' }]
}
beforeEach(async () => {
  calls = []; replies = {}
  configuration.items = [{ config_key: 'decision_threshold', value: 0.5 }]
  configuration.ready = true
  job = { job_id: 'test-job', kind: 'predict_batch', status: 'success', total: 2, done: 2, retry_count: 0,
    output_ref_json: { outputs: outputs(), summary: { input_rows: 2, success_count: 2, failed_count: 0, model_name: 'lr_v1', decision_threshold: 0.5 } } }
  const status = { default_model: 'lr_v1', fallback_reason: null, items: [
    { model_name: 'lr_v1', line: 'expert', algo: 'lr', artifact_status: 'available', runtime_state: 'loaded', load_error: null, version_key: 'v1', feature_version: 'v1', checksum_sha256: 'c'.repeat(64) }] }
  request.defaults.adapter = async cfg => {
    calls.push(cfg)
    const value = await (replies[cfg.url]?.shift() ?? (cfg.url === '/models/status' ? status
      : cfg.url === '/models' ? { lines: [{ line: 'expert', label: '专家', models: ['lr_v1'] }] }
        : cfg.url === '/datasets' ? { items: [], total: 0 }
          : cfg.url === '/jobs' ? { items: [], total: 0 }
            : cfg.url === '/predict/run' ? { job_id: job.job_id, status: job.status }
              : cfg.url === '/models/default' ? { default_model: 'lr_v1' }
                : /\/models\/[^/]+\/(load|unload|reload)$/.test(cfg.url) ? { model_name: 'lr_v1', runtime_state: 'loaded', load_error: null }
                  : cfg.url.endsWith('/retry') ? { job_id: job.job_id, status: 'queued', retry_count: 1 }
                    : cfg.url.endsWith('/cancel') ? { job_id: job.job_id, status: 'cancelled' }
                      : cfg.url === '/storage/import' ? { items: [{ status: 'success' }], summary: { inserted: 2, rejected: 0 } } : job))
    const response = { config: cfg, headers: {}, status: value?.code ? 400 : 200, data: value?.code ? value : { code: 0, data: value } }
    if (value?.code) throw new AxiosError('failed', 'ERR_BAD_RESPONSE', cfg, null, response)
    return response
  }
  fetchMock = vi.fn(async (url) => ({ ok: true, blob: async () => new Blob([url.endsWith('.csv') ? csvText : url.endsWith('summary_test-job.json') ? JSON.stringify(job.output_ref_json.summary) : 'file']) }))
  vi.stubGlobal('fetch', fetchMock)
  class TestURL extends URL {}
  Object.assign(TestURL, { createObjectURL: vi.fn(() => 'blob:predict-test'), revokeObjectURL: vi.fn() })
  vi.stubGlobal('URL', TestURL)
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  const stores = import.meta.glob('../src/utils/predict.js')
  if (stores['../src/utils/predict.js']) Object.assign((await stores['../src/utils/predict.js']()).predicting, { job: null, request: null })
})
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = ''; request.defaults.adapter = adapter; vi.restoreAllMocks(); vi.unstubAllGlobals() })
async function open() {
  expect(Predict, 'real predict view must exist').toBeDefined()
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/predict', component: Predict }] })
  await router.push('/predict'); await router.isReady()
  wrapper = mount(Predict, { attachTo: document.body, global: { plugins: [ElementPlus, router] } }); await flushPromises()
}
async function upload() {
  const input = wrapper.get('#predict-files')
  Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['zip'], 'model_package.zip'), new File(['table'], 'cleaned.csv')] })
  await input.trigger('change')
}
async function click(id) { await wrapper.get(`[data-testid="${id}"]`).trigger('click'); await flushPromises() }
const last = url => calls.filter(call => call.url === url).at(-1)

it('wires real predict route', async () => {
  expect(Predict).toBeDefined()
  const router = (await import('../src/router')).default
  expect(router.options.routes.find(route => route.path === '/predict')?.component).toBe((await import('../src/views/PredictWorkbench.vue')).default)
})
it('renders model status and triggers load/unload/reload/default', async () => {
  await open()
  expect(wrapper.get('[data-testid="predict-models"]').text()).toContain('lr_v1')
  await click('predict-load-lr_v1'); expect(last('/models/lr_v1/load')).toBeDefined()
  await click('predict-reload-lr_v1'); expect(last('/models/lr_v1/reload')).toBeDefined()
  await click('predict-unload-lr_v1'); expect(last('/models/lr_v1/unload')).toBeDefined()
})
it('runs with uploaded zip plus feature file and no automatic import', async () => {
  await open(); await upload(); await click('predict-run')
  expect(last('/predict/run').data.getAll('files[]').map(f => f.name)).toEqual(['model_package.zip', 'cleaned.csv'])
  expect(last('/storage/import')).toBeUndefined()
})
it('retains draft and disables run without inputs', async () => {
  await open(); await click('predict-run')
  expect(last('/predict/run')).toBeUndefined()
  expect(wrapper.text()).toContain('上传')
  expect(wrapper.get('[data-testid="predict-run"]').attributes('disabled')).toBeDefined()
})
it('submits threshold and force_recompute', async () => {
  await open(); await upload()
  await wrapper.get('#predict-threshold').setValue(0.7)
  await wrapper.get('#predict-force').setValue(true)
  await click('predict-run')
  const sent = JSON.parse(last('/predict/run').data.get('config'))
  expect(sent.decision_threshold).toBe(0.7)
  expect(sent.force_recompute).toBe(true)
})
it('parses preview csv showing unlabeled as 未打标 not zero', async () => {
  await open(); await upload(); await click('predict-run')
  const text = wrapper.get('[data-testid="predict-preview"]').text()
  expect(text).toContain('0.83000')
  expect(text).toContain('未打标')
})
it('downloads predictions and imports only after explicit action', async () => {
  await open(); await upload(); await click('predict-run')
  await click('predict-download-predict_predictions_test-job.csv')
  expect(fetchMock.mock.calls.some(([u]) => u.endsWith('.csv'))).toBe(true)
  expect(last('/storage/import')).toBeUndefined()
  await click('predict-import')
  expect(last('/storage/import').data.getAll('files[]').map(f => f.name)).toEqual(['predict_predictions_test-job.csv'])
})
it('keeps draft on backend validation error', async () => {
  replies['/predict/run'] = [{ code: 40001, message: 'checksum 不符' }]
  await open(); await upload(); await click('predict-run')
  expect(wrapper.text()).toContain('checksum 不符')
  expect(wrapper.text()).toContain('model_package.zip')
})
it('retries original job and cancels running job', async () => {
  job.status = 'failed'; job.error_log = 'boom'
  await open(); await upload(); await click('predict-run'); await click('predict-retry')
  expect(last('/jobs/test-job/retry')).toBeDefined()
  expect(calls.filter(c => c.url === '/predict/run')).toHaveLength(1)
  job.status = 'running'
  await click('predict-run'); await click('predict-cancel')
  expect(last('/jobs/test-job/cancel')).toBeDefined()
})
it('uses registered model convenience without uploading a zip', async () => {
  await open()
  await wrapper.get('#predict-registered').setValue('lr_v1')
  const input = wrapper.get('#predict-files')
  Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['table'], 'cleaned.csv')] })
  await input.trigger('change')
  await click('predict-run')
  const sent = JSON.parse(last('/predict/run').data.get('config'))
  expect(sent.model_name).toBe('lr_v1')
  expect(last('/predict/run').data.getAll('files[]').map(f => f.name)).toEqual(['cleaned.csv'])
})
