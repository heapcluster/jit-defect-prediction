import { afterAll, afterEach, beforeAll, beforeEach, expect, it, vi } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import { AxiosError } from 'axios'
import request from '../src/api/request'
import { configuration } from '../src/utils/thresholds'

const views = import.meta.glob('../src/views/*.vue')
const Explain = views['../src/views/Explain.vue'] ? (await views['../src/views/Explain.vue']()).default : undefined
const adapter = request.defaults.adapter, loading = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = loading })
let wrapper, calls, replies, registry, job, comparison, fetchMock, history, sourceJobs
const techniques = [
  { key: 'shap', name: 'SHAP', description: '全局背景上的特征贡献', params_schema: [
    { name: 'background_size', type: 'int', default: 40, min: 1, max: 200, description: '背景数量' },
    { name: 'regularization', type: 'float', default: 0.5, min: 0, max: 1 },
    { name: 'mode', type: 'string', default: 'auto', choices: ['auto', 'linear'] },
    { name: 'limit', type: 'int', default: null, min: 1 }
  ] },
  { key: 'lime', name: 'LIME', description: '局部概率系数', params_schema: [
    { name: 'num_samples', type: 'integer', default: 100, min: 1, max: 10000 },
    { name: 'kernel_width', type: 'number', default: 0.75, min: 0.01, max: 3 },
    { name: 'discretize', type: 'boolean', default: true }
  ] }
]
function outputs(id = 'explain-one') {
  return [
    { name: `explain_comparison_${id}.json`, sha256: 'abc123', size_bytes: 123 },
    { name: `explain_contributions_${id}.png`, sha256: 'def456', size_bytes: 456 },
    { name: `explain_results_${id}.csv`, sha256: 'ghi789', size_bytes: 789 }
  ]
}
function successful(id = 'explain-one') {
  return { job_id: id, kind: 'explain', status: 'success', total: 2, done: 2,
    output_ref_json: { outputs: outputs(id), summary: { input_rows: 1, success_count: 2, techniques: ['shap', 'lime'], reason_counts: {}, cache_hits: 1 } } }
}
function deferred() { let resolve; const promise = new Promise(r => { resolve = r }); return { promise, resolve } }
function blobResponse(content) { return { ok: true, blob: async () => new Blob([content]) } }
beforeEach(() => {
  calls = []; replies = {}; history = []; sourceJobs = {}; job = successful()
  registry = { techniques, compatibility: [{ family: 'linear', technique: 'shap', supported: true, reason_code: null }], default_technique: 'shap', compare_enabled: true }
  configuration.items = [{ config_key: 'default_xai', value: 'shap' }]; configuration.ready = true
  configuration.schema = {}
  comparison = {
    rows: [
      { commit_hash: 'abc', model_name: 'loaded-model', technique: 'shap', feature: 'la', raw_value: 7, contribution: -0.125, direction: 'decrease', rank: 1, model_version: 'm1', feature_version: 'f1', label: 1 },
      { commit_hash: 'abc', technique: 'shap', feature: 'ld', raw_value: 0, contribution: 0, direction: 'neutral', rank: 3 },
      { commit_hash: 'abc', technique: 'lime', feature: 'la', raw_value: 7, contribution: 0.25, direction: 'increase', rank: 1 },
      { commit_hash: 'unsupported', technique: 'shap', feature: null, contribution: null, reason_code: 'unsupported_family' }
    ],
    results: [
      { commit_hash: 'abc', technique: 'shap', items: [{ feature: 'la', contribution: -0.125, direction: 'decrease', rank: 1, output_space: 'log_odds' }], base_value: -0.4, output_space: 'log_odds' },
      { commit_hash: 'abc', technique: 'lime', items: [{ feature: 'la', contribution: 0.25, direction: 'increase', rank: 1, output_space: 'local_probability_coefficient' }], base_value: 0.6, output_space: 'local_probability_coefficient', message: '局部近似' }
    ], summary: { input_rows: 2, success_count: 2, techniques: ['shap', 'lime'], reason_counts: { unsupported_family: 1 }, cache_hits: 1 }
  }
  request.defaults.adapter = async cfg => {
    calls.push(cfg)
    const responseOverride = replies[cfg.url]?.shift()
    const value = await (responseOverride ?? (cfg.url === '/explain/techniques' ? registry
      : cfg.url === '/models' ? { lines: [{ line: 'expert', label: '专家特征', models: [{ model_name: 'loaded-model', loaded: true, family: 'linear' }, { model_name: 'unloaded-model', loaded: false }] }] }
        : cfg.url === '/datasets' ? { items: [{ dataset_id: 'data-one', name: '已导入表格' }] }
          : cfg.url === '/jobs' ? { items: cfg.params.kind === 'explain' ? history : sourceJobs[cfg.params.kind] || [] }
            : cfg.url === '/explain/run' ? { job_id: job.job_id, status: job.status }
              : cfg.url === '/config' ? { items: [{ config_key: 'risk_high_threshold', value: 0.7 }, { config_key: 'risk_mid_threshold', value: 0.4 }, { config_key: 'default_xai', value: 'lime' }], schema: { risk_high_threshold: {}, risk_mid_threshold: {}, default_xai: {} } }
                : cfg.url.startsWith('/config/') ? {}
                  : cfg.url.endsWith('/retry') ? { job_id: job.job_id, status: 'queued' }
                    : cfg.url.endsWith('/cancel') ? { job_id: job.job_id, status: 'cancelled' } : job))
    const response = { config: cfg, headers: {}, status: value?.code ? 400 : 200, data: value?.code ? value : { code: 0, data: JSON.parse(JSON.stringify(value)) } }
    if (value?.code) throw new AxiosError('failed', 'ERR_BAD_RESPONSE', cfg, null, response)
    return response
  }
  fetchMock = vi.fn(async url => blobResponse(url.includes('explain_comparison_') ? JSON.stringify(comparison) : 'server artifact'))
  vi.stubGlobal('fetch', fetchMock)
  class TestURL extends URL {}
  let next = 0
  Object.assign(TestURL, { createObjectURL: vi.fn(() => `blob:explain-${++next}`), revokeObjectURL: vi.fn() })
  vi.stubGlobal('URL', TestURL)
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
})
afterEach(() => {
  wrapper?.unmount(); wrapper = null; document.body.innerHTML = ''
  request.defaults.adapter = adapter; vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers()
})
async function open() {
  expect(Explain, 'real Explain.vue must exist').toBeDefined()
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/explain', component: Explain }, { path: '/predict', component: { template: '<div />' } }] })
  await router.push('/explain'); await router.isReady()
  wrapper = mount(Explain, { attachTo: document.body, global: { plugins: [ElementPlus, router] } }); await flushPromises()
}
async function upload(names = ['commits.csv']) {
  const input = wrapper.get('#explain-files')
  const files = names.map(name => new File(['not parsed in browser'], name))
  Object.defineProperty(input.element, 'files', { configurable: true, value: files })
  await input.trigger('change'); return files
}
async function click(id) { await wrapper.get(`[data-testid="${id}"]`).trigger('click'); await flushPromises() }
const last = url => calls.filter(c => c.url === url).at(-1)
const payload = () => JSON.parse(last('/explain/run').data.get('config'))
async function ready() { await upload(); await wrapper.get('#explain-model').setValue('loaded-model') }

it('provides the real explanation view', () => { expect(Explain, 'real Explain.vue must exist').toBeDefined() })
it('renders registry techniques, typed parameters, compatibility and default', async () => {
  await open()
  expect(wrapper.findAll('[data-testid="explain-technique"]')).toHaveLength(2)
  expect(wrapper.get('#explain-technique-shap').element.checked).toBe(true)
  expect(wrapper.get('#explain-param-shap-background_size').element.step).toBe('1')
  expect(wrapper.get('#explain-param-shap-regularization').element.step).toBe('any')
  expect(wrapper.text()).toContain('linear')
})
it('runs a single unparsed file without database path or predictions', async () => {
  replies['/datasets'] = [{ items: [] }]
  await open(); const files = await upload(); await wrapper.get('#explain-model').setValue('loaded-model'); await click('explain-run')
  expect(last('/explain/run').data.getAll('files[]')[0].name).toBe(files[0].name)
  expect(payload()).toMatchObject({ techniques: ['shap'], top_n: 8, format: 'csv', model_name: 'loaded-model' })
  expect(payload()).not.toHaveProperty('db_path')
  expect(calls.some(c => /\/storage\/import|\/train\/run|\/predict\/run/.test(c.url))).toBe(false)
  expect(wrapper.find('[data-testid="explain-import"]').exists()).toBe(false)
})
it('runs an uploaded model ZIP and table independently of an empty model registry', async () => {
  replies['/models'] = [{ lines: [] }]; replies['/datasets'] = [{ items: [] }]
  await open(); await upload(['model.zip', 'model.manifest.json', 'cleaned.xlsx']); await click('explain-run')
  expect(last('/explain/run').data.getAll('files[]').map(f => f.name)).toEqual(['model.zip', 'model.manifest.json', 'cleaned.xlsx'])
  expect(payload()).not.toHaveProperty('model_name')
})
it('supports dataset convenience with an uploaded ZIP', async () => {
  await open(); await upload(['model.zip']); await wrapper.get('#explain-dataset').setValue('data-one'); await click('explain-run')
  expect(payload().dataset_id).toBe('data-one')
})
it('links loaded-model management and prevents missing inputs', async () => {
  await open()
  expect(wrapper.get('a[href="/predict"]').exists()).toBe(true)
  expect(wrapper.get('#explain-model option[value="unloaded-model"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('#explain-run').attributes('disabled')).toBeDefined()
  await upload(); expect(wrapper.get('#explain-run').attributes('disabled')).toBeDefined()
})
it('saves only the selected default and reloads configuration without a run', async () => {
  await open(); await wrapper.get('#explain-default').setValue('lime'); await click('explain-save-default')
  expect(JSON.parse(last('/config/default_xai').data)).toEqual({ value: 'lime' })
  expect(last('/config')).toBeDefined(); expect(last('/explain/run')).toBeUndefined()
})
it('requires server comparison enablement and limits selection to one technique', async () => {
  registry.compare_enabled = false
  await open(); await ready()
  expect(wrapper.get('#explain-compare').attributes('disabled')).toBeDefined()
  await wrapper.get('#explain-technique-lime').setValue(true)
  await click('explain-run')
  expect(payload().techniques).toEqual(['lime'])
})
it('enables comparison only by explicit config PUT and registry refresh', async () => {
  registry.compare_enabled = false; await open()
  expect(last('/config/explain.compare_enabled')).toBeUndefined()
  registry.compare_enabled = true; await click('explain-enable-compare')
  expect(JSON.parse(last('/config/explain.compare_enabled').data)).toEqual({ value: true })
  expect(wrapper.get('#explain-compare').attributes('disabled')).toBeUndefined()
})
it('submits explicit two-technique normalized JSON, output format and commit filters', async () => {
  await open(); await ready(); await wrapper.get('#explain-compare').setValue(true); await wrapper.get('#explain-technique-lime').setValue(true)
  await wrapper.get('#explain-param-shap-background_size').setValue('32')
  await wrapper.get('#explain-param-shap-regularization').setValue('0.125')
  await wrapper.get('#explain-param-lime-num_samples').setValue('250')
  await wrapper.get('#explain-param-lime-kernel_width').setValue('1.25')
  await wrapper.get('#explain-param-lime-discretize').setValue(false)
  await wrapper.get('#explain-top-n').setValue('6'); await wrapper.get('#explain-format').setValue('xlsx')
  await wrapper.get('#explain-commit-hashes').setValue('abc, def\nabc'); await wrapper.get('#explain-cache-ttl').setValue('90')
  await click('explain-run')
  expect(payload()).toEqual({ techniques: ['shap', 'lime'], params: { shap: { background_size: 32, regularization: 0.125, mode: 'auto' }, lime: { num_samples: 250, kernel_width: 1.25, discretize: false } }, top_n: 6, format: 'xlsx', cache_ttl: 90, commit_hashes: ['abc', 'def'], model_name: 'loaded-model' })
})
it('validates integers and schema bounds without discarding drafts', async () => {
  await open(); await ready(); await wrapper.get('#explain-param-shap-background_size').setValue('2.5'); await click('explain-run')
  expect(last('/explain/run')).toBeUndefined(); expect(wrapper.text()).toContain('background_size')
  expect(wrapper.text()).toContain('commits.csv')
})
it('does not supply fallback techniques when metadata fails and offers retry', async () => {
  replies['/explain/techniques'] = [{ code: 50000, message: 'registry unavailable' }]
  await open(); await ready()
  expect(wrapper.findAll('[data-testid="explain-technique"]')).toHaveLength(0)
  expect(wrapper.get('#explain-run').attributes('disabled')).toBeDefined()
  await click('explain-retry-metadata'); expect(wrapper.findAll('[data-testid="explain-technique"]')).toHaveLength(2)
  expect(wrapper.text()).toContain('commits.csv')
})
it('downloads only registered companions and retains one file per input role', async () => {
  sourceJobs = {
    train: [{ job_id: 'train-one', kind: 'train', output_ref_json: { outputs: [{ name: 'model.zip' }] } }],
    clean: [{ job_id: 'clean-one', kind: 'clean', output_ref_json: { outputs: [{ name: 'cleaned.csv' }, { name: 'cleaned.manifest.json' }] } }],
    predict_batch: [{ job_id: 'predict-one', kind: 'predict_batch', output_ref_json: { outputs: [{ name: 'predictions.csv' }, { name: 'predictions.manifest.json' }] } }]
  }
  await open(); await upload(['old.csv', 'older.csv', 'old.zip', 'old.manifest.json'])
  await wrapper.get('#explain-source-artifact').setValue('train/train-one/model.zip'); await click('explain-use-artifact')
  expect(fetchMock.mock.calls.map(([u]) => u).filter(u => u.includes('/train/'))).toEqual(['/api/train/outputs/train-one/model.zip'])
  await wrapper.get('#explain-source-artifact').setValue('clean/clean-one/cleaned.csv'); await click('explain-use-artifact')
  await wrapper.get('#explain-source-artifact').setValue('predict_batch/predict-one/predictions.csv'); await click('explain-use-artifact')
  await click('explain-run')
  const names = last('/explain/run').data.getAll('files[]').map(f => f.name)
  expect(names.sort()).toEqual(['model.zip', 'cleaned.csv', 'cleaned.manifest.json', 'predictions.csv', 'predictions.manifest.json'].sort())
})
it('shows source loading failures and retries without replacing uploaded drafts', async () => {
  replies['/jobs'] = [{ code: 50000, message: 'sources unavailable' }]
  await open(); await upload(); expect(wrapper.get('[data-testid="explain-source-error"]').text()).toBeTruthy()
  await click('explain-retry-sources'); expect(wrapper.text()).toContain('commits.csv')
})
it('renders literal null reason contributions as empty, signed negatives and neutral zero with rank', async () => {
  await open(); await ready(); await click('explain-run')
  const rows = wrapper.findAll('[data-testid="explain-row"]')
  expect(rows[0].text()).toContain('-0.125000')
  expect(rows[1].get('[data-testid="explain-contribution"]').text()).toBe('0.000000')
  expect(rows[1].text()).toContain('3')
  expect(rows[3].get('[data-testid="explain-contribution"]').text()).toBe('')
  expect(rows[3].get('[data-testid="explain-feature"]').text()).toBe('')
  expect(rows[3].text()).toContain('unsupported_family')
})
it('shows two first-commit comparisons, baselines, spaces and signed zero-centered bars', async () => {
  await open(); await ready(); await click('explain-run')
  expect(wrapper.findAll('[data-testid="explain-comparison-technique"]')).toHaveLength(2)
  expect(wrapper.get('[data-testid="explain-comparison"]').text()).toContain('log_odds')
  expect(wrapper.text()).toContain('tree_raw'); expect(wrapper.text()).toContain('local_probability_coefficient')
  expect(wrapper.text()).toContain('非精确加性'); expect(wrapper.text()).toContain('-0.400000')
  expect(wrapper.find('.contribution-bar.decrease').exists()).toBe(true)
  expect(wrapper.find('.contribution-bar.increase').exists()).toBe(true)
  expect(wrapper.get('[data-testid="explain-summary"]').text()).toContain('2 × 2')
})
it('limits preview to twenty rows and surfaces empty results and reasons', async () => {
  comparison.rows = Array.from({ length: 25 }, (_, i) => ({ commit_hash: String(i), feature: 'la', contribution: 1, direction: 'increase' }))
  await open(); await ready(); await click('explain-run'); expect(wrapper.findAll('[data-testid="explain-row"]')).toHaveLength(20)
  comparison.rows = []; comparison.results = []; comparison.summary.reason_counts = { no_features: 2 }
  await click('explain-run'); expect(wrapper.text()).toContain('暂无可解释贡献'); expect(wrapper.text()).toContain('no_features')
})
it('fetches authenticated comparison and PNG, lists metadata and releases every URL', async () => {
  await open(); await ready(); await click('explain-run')
  expect(fetchMock.mock.calls.every(([, o]) => 'X-API-Key' in o.headers)).toBe(true)
  expect(fetchMock.mock.calls.some(([u]) => u.endsWith('explain_comparison_explain-one.json'))).toBe(true)
  expect(wrapper.get('[data-testid="explain-output-list"]').text()).toContain('abc123')
  expect(wrapper.get('[data-testid="explain-output-list"]').text()).toContain('123')
  await click('explain-download-explain_results_explain-one.csv')
  expect(fetchMock.mock.calls.some(([u]) => u.endsWith('.csv'))).toBe(true)
  const urls = URL.createObjectURL.mock.results.map(r => r.value)
  wrapper.unmount(); wrapper = null
  for (const url of urls) expect(URL.revokeObjectURL).toHaveBeenCalledWith(url)
})
it('stages PNG and comparison atomically on output errors', async () => {
  fetchMock.mockImplementation(async url => url.endsWith('.json') ? { ok: false, status: 500, json: async () => ({ message: 'temporary' }) } : blobResponse('png'))
  await open(); await ready(); await click('explain-run')
  expect(URL.createObjectURL).not.toHaveBeenCalled(); expect(wrapper.find('[data-testid="explain-figure"]').exists()).toBe(false)
  fetchMock.mockImplementation(async url => blobResponse(url.endsWith('.json') ? JSON.stringify(comparison) : 'png'))
  await click('explain-retry-output'); expect(wrapper.find('[data-testid="explain-figure"]').exists()).toBe(true)
})
it('stops on authenticated output failures and preserves the form', async () => {
  fetchMock.mockResolvedValue({ ok: false, status: 401, json: async () => ({ code: 40100, message: 'unauthorized' }) })
  await open(); await ready(); await click('explain-run')
  expect(wrapper.text()).toContain('API Key'); expect(wrapper.get('#explain-run').attributes('disabled')).toBeDefined()
  expect(wrapper.text()).toContain('commits.csv'); expect(URL.createObjectURL).not.toHaveBeenCalled()
})
it('restores the latest exact explain job on remount', async () => {
  history = [successful()]; await open()
  expect(calls.some(c => c.url === '/jobs' && c.params.kind === 'explain' && c.params.size === 1)).toBe(true)
  expect(last('/jobs/explain-one')).toBeDefined()
  wrapper.unmount(); wrapper = null; await open(); expect(wrapper.text()).toContain('explain-one')
})
it('retries the original failed job without form overrides and cancels running by id', async () => {
  job = { job_id: 'original', kind: 'explain', status: 'failed', error_log: 'failed input' }; history = [job]
  await open(); await upload(['different.csv']); await click('explain-retry')
  expect(last('/jobs/original/retry')).toBeDefined(); expect(last('/jobs/original/retry').data).toBeUndefined(); expect(last('/explain/run')).toBeUndefined()
  job.status = 'running'; await click('explain-refresh-job'); await click('explain-cancel')
  expect(last('/jobs/original/cancel')).toBeDefined(); expect(wrapper.text()).toContain('cancelled')
})
it('polls through transient failures then stops after success', async () => {
  vi.useFakeTimers(); job = { job_id: 'poll', kind: 'explain', status: 'running', total: 2, done: 0 }; history = [job]
  replies['/jobs/poll'] = [{ code: 50000, message: 'temporary' }, successful('poll')]
  await open(); await vi.advanceTimersByTimeAsync(1500); await flushPromises()
  expect(wrapper.text()).toContain('success')
  const count = calls.length; await vi.advanceTimersByTimeAsync(6000); expect(calls.length).toBe(count)
})
it('stops authentication polling and clears timers on unmount', async () => {
  vi.useFakeTimers(); job = { job_id: 'poll', kind: 'explain', status: 'running' }; history = [job]
  replies['/jobs/poll'] = [{ code: 40100, message: 'expired' }]
  await open(); const count = calls.length; await vi.advanceTimersByTimeAsync(6000); expect(calls.length).toBe(count)
  wrapper.unmount(); wrapper = null; await vi.advanceTimersByTimeAsync(6000); expect(calls.length).toBe(count)
})
it('prevents stale output from committing after a new job', async () => {
  const pending = deferred(); history = [successful('old')]; job = successful('old')
  fetchMock.mockImplementation(async url => url.includes('comparison_old') ? pending.promise : blobResponse(url.endsWith('.json') ? JSON.stringify(comparison) : 'png'))
  await open(); await ready(); job = successful('new'); await click('explain-run')
  expect(wrapper.text()).toContain('new'); const count = URL.createObjectURL.mock.calls.length
  pending.resolve(blobResponse(JSON.stringify({ ...comparison, rows: [{ feature: 'STALE', contribution: 10 }] }))); await flushPromises()
  expect(wrapper.text()).not.toContain('STALE'); expect(URL.createObjectURL.mock.calls.length).toBe(count)
})
it('discards late output after unmount without creating URLs', async () => {
  const pending = deferred(); history = [successful()]
  fetchMock.mockImplementation(async url => url.endsWith('.json') ? pending.promise : blobResponse('png'))
  await open(); wrapper.unmount(); wrapper = null; pending.resolve(blobResponse(JSON.stringify(comparison))); await flushPromises()
  expect(URL.createObjectURL).not.toHaveBeenCalled()
})
