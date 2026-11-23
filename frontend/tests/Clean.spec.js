// AI-generated W4 tests, not human-reviewed.
import { afterAll, afterEach, beforeAll, beforeEach, expect, it, vi } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import { AxiosError } from 'axios'
import request from '../src/api/request'
import { configuration } from '../src/utils/thresholds'
import { FEATURE_FIELDS } from '../src/utils/features'

const views = import.meta.glob('../src/views/*.vue')
const Clean = views['../src/views/Clean.vue'] ? (await views['../src/views/Clean.vue']()).default : undefined
const names = ['merge_filter', 'szz_label', 'd5_exclude', 'anomaly_exclude', 'label_validate', 'feature_align', 'log_transform', 'standardize', 'time_split']
const operations = names.map(op => ({ op, name: '服务端 ' + op, description: '真实注册表说明', default_enabled: !['standardize', 'anomaly_exclude'].includes(op),
  params_schema: op === 'time_split' ? [{ name: 'ratio', type: 'float', default: 0.7, min: 0.01, max: 0.99 }] : [],
  order_constraints: op === 'time_split' ? [{ type: 'last' }] : op === 'merge_filter' ? [{ type: 'first' }] : [], supports_preview: true }))
const adapter = request.defaults.adapter, loading = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = loading })
let wrapper, calls, replies, job, fetchMock
function entries(mode) {
  return [...(mode === 'apply' ? [{ name: 'clean_cleaned_test-job.csv' }, { name: 'clean_cleaned_test-job.xlsx' }, { name: 'clean_cleaned_test-job.manifest.json' }] : []),
    { name: 'clean_steps_stats_test-job.json' }, { name: 'clean_feature_stats_test-job.json' }, { name: 'clean_feature_distribution_ns_test-job.png' }]
}
beforeEach(async () => {
  calls = []; replies = {}
  configuration.items = []; configuration.ready = true
  job = { job_id: 'test-job', kind: 'clean', status: 'success', total: 10, done: 10, retry_count: 0,
    output_ref_json: { mode: 'preview', outputs: entries('preview'), summary: { input_rows: 4, output_rows: 3, warnings: [] } } }
  request.defaults.adapter = async cfg => {
    calls.push(cfg)
    const value = await (replies[cfg.url]?.shift() ?? (cfg.url === '/clean/operations' ? { operations, features: FEATURE_FIELDS }
      : cfg.url === '/datasets' ? { items: [], total: 0 }
        : cfg.url === '/jobs' ? { items: [], total: 0 }
          : cfg.url === '/clean/run' ? { job_id: job.job_id, status: job.status }
            : cfg.url.endsWith('/retry') ? { job_id: job.job_id, status: 'queued', retry_count: 1 }
              : cfg.url.endsWith('/cancel') ? { job_id: job.job_id, status: 'cancelled' }
                : cfg.url === '/clean/preview/test-job' ? { columns: ['commit_hash', 'is_bug_inducing'], preview: [{ commit_hash: 'a'.repeat(40), is_bug_inducing: null }] }
                  : cfg.url === '/storage/import' ? { items: [{ status: 'success' }], summary: { inserted: 3, rejected: 0 } } : job))
    const response = { config: cfg, headers: {}, status: value?.code ? 400 : 200, data: value?.code ? value : { code: 0, data: value } }
    if (value?.code) throw new AxiosError('failed', 'ERR_BAD_RESPONSE', cfg, null, response)
    return response
  }
  fetchMock = vi.fn(async url => ({ ok: true, blob: async () => new Blob([url.includes('steps_stats') ? JSON.stringify([{ op: 'd5_exclude', rows_before: 4, rows_after: 3, removed: 1, modified: 0, label_dist: { positive: 1, negative: 2, unlabeled: 0 }, elapsed_ms: 2, excluded_samples: [{ commit_hash: 'b'.repeat(40), reason: 'unresolved_fix' }] }]) : url.includes('feature_stats') ? '{}' : 'server file']) }))
  vi.stubGlobal('fetch', fetchMock)
  class TestURL extends URL {}
  Object.assign(TestURL, { createObjectURL: vi.fn(() => 'blob:clean-test'), revokeObjectURL: vi.fn() })
  vi.stubGlobal('URL', TestURL)
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  const stores = import.meta.glob('../src/utils/clean.js')
  if (stores['../src/utils/clean.js']) Object.assign((await stores['../src/utils/clean.js']()).cleaning, { job: null, request: null })
})
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = ''; request.defaults.adapter = adapter; vi.restoreAllMocks(); vi.unstubAllGlobals() })
async function open() {
  expect(Clean, 'real independent clean view must exist').toBeDefined()
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/clean', component: Clean }] })
  await router.push('/clean'); await router.isReady()
  wrapper = mount(Clean, { attachTo: document.body, global: { plugins: [ElementPlus, router] } }); await flushPromises()
}
async function upload() {
  const input = wrapper.get('#clean-files')
  Object.defineProperty(input.element, 'files', { configurable: true, value: [new File(['table'], 'commits.csv'), new File(['{}'], 'commits.manifest.json')] })
  await input.trigger('change')
}
async function click(id) { await wrapper.get(`[data-testid="${id}"]`).trigger('click'); await flushPromises() }
const last = url => calls.filter(call => call.url === url).at(-1)

it('wires real clean route', async () => {
  const router = (await import('../src/router')).default
  expect(router.options.routes.find(route => route.path === '/clean')?.component).toBe(Clean)
  expect(Clean).toBeDefined()
})
it('renders nine operations and parameter defaults from API', async () => {
  await open()
  expect(wrapper.findAll('[data-testid="clean-step"]')).toHaveLength(9)
  expect(wrapper.text()).toContain('服务端 time_split')
  expect(wrapper.get('#clean-param-time_split-ratio').element.value).toBe('0.7')
})
it('runs with uploaded file plus manifest and no dataset prerequisite', async () => {
  await open(); await upload(); await click('clean-run')
  expect(last('/clean/run').data.getAll('files[]').map(file => file.name)).toEqual(['commits.csv', 'commits.manifest.json'])
  expect(JSON.parse(last('/clean/run').data.get('config')).features).toEqual(FEATURE_FIELDS)
  expect(last('/storage/import')).toBeUndefined()
})
it('keeps missing-file draft and does not send run', async () => {
  await open(); await wrapper.get('#clean-seed').setValue(123); await click('clean-run')
  expect(last('/clean/run')).toBeUndefined()
  expect(wrapper.text()).toContain('上传')
  expect(wrapper.get('#clean-seed').element.value).toBe('123')
})
it('rejects an empty feature selection before submitting', async () => {
  await open(); await upload()
  for (const input of wrapper.findAll('[data-testid="clean-feature"]')) await input.setValue(false)
  expect(wrapper.get('[data-testid="clean-run"]').attributes('disabled')).toBeDefined()
  expect(wrapper.text()).toContain('至少选择一个')
})
it('supports enabling a step and submitting actual parameters', async () => {
  await open(); await upload()
  await wrapper.get('#clean-enabled-anomaly_exclude').setValue(true)
  await wrapper.get('#clean-param-time_split-ratio').setValue(0.8)
  await click('clean-run')
  const sent = JSON.parse(last('/clean/run').data.get('config'))
  expect(sent.steps.find(step => step.op === 'anomaly_exclude').enabled).toBe(true)
  expect(sent.steps.find(step => step.op === 'time_split').params.ratio).toBe(0.8)
})
it('reports order conflicts when moving the final time split up', async () => {
  await open(); await upload(); await click('clean-up-time_split'); await click('clean-up-time_split')
  expect(wrapper.text()).toContain('顺序')
  expect(wrapper.get('[data-testid="clean-run"]').attributes('disabled')).toBeDefined()
})
it('renders real exclusions and PNG via authenticated fetch without preview main table', async () => {
  await open(); await upload(); await click('clean-run')
  expect(wrapper.text()).toContain('unresolved_fix')
  expect(wrapper.find('[data-testid="clean-preview"]').exists()).toBe(false)
  expect(wrapper.find('[data-testid="clean-import"]').exists()).toBe(false)
  expect(wrapper.findAll('img')).toHaveLength(1)
  expect(fetchMock.mock.calls.every(([, options]) => 'X-API-Key' in options.headers)).toBe(true)
})
it('apply shows NULL and imports only after explicit action', async () => {
  job.output_ref_json = { mode: 'apply', outputs: entries('apply'), summary: { input_rows: 4, output_rows: 3, warnings: [] } }
  await open(); await upload(); await wrapper.get('#clean-mode').setValue('apply'); await click('clean-run')
  expect(wrapper.get('[data-testid="clean-preview"]').text()).toContain('未打标')
  expect(last('/storage/import')).toBeUndefined()
  await wrapper.get('#clean-import-name').setValue('new version')
  await wrapper.get('#clean-import-source').setValue('fixture')
  await click('clean-import')
  expect(last('/storage/import').data.getAll('files[]').map(file => file.name)).toEqual(['clean_cleaned_test-job.csv', 'clean_cleaned_test-job.manifest.json'])
})
it('downloads actual output and releases image URLs on unmount', async () => {
  await open(); await upload(); await click('clean-run'); await click('clean-download-clean_steps_stats_test-job.json')
  expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/clean_steps_stats_test-job.json'))).toBe(true)
  wrapper.unmount(); wrapper = null
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:clean-test')
})
it('stages image output atomically and does not duplicate on refresh after a failure', async () => {
  job.output_ref_json.outputs.push({ name: 'clean_feature_distribution_nd_test-job.png' })
  const original = fetchMock.getMockImplementation()
  let fail = true
  fetchMock.mockImplementation(async (...args) => {
    if (fail && args[0].includes('distribution_nd')) throw new Error('image failed')
    return original(...args)
  })
  await open(); await upload(); await click('clean-run')
  expect(wrapper.findAll('img')).toHaveLength(0)
  fail = false
  await wrapper.get('[data-testid="clean-job"] .el-button').trigger('click'); await flushPromises()
  expect(wrapper.findAll('img')).toHaveLength(2)
})
it('ignores stale preview response and restarts the replacement job poll', async () => {
  job.output_ref_json = { mode: 'apply', outputs: entries('apply'), summary: { input_rows: 4, output_rows: 3, warnings: [] } }
  const original = fetchMock.getMockImplementation()
  let failImage = true, release
  fetchMock.mockImplementation(async (...args) => {
    if (failImage && args[0].endsWith('.png')) throw new Error('image failed')
    return original(...args)
  })
  await open(); await upload(); await click('clean-run')
  failImage = false
  replies['/clean/preview/test-job'] = [new Promise(resolve => { release = resolve })]
  await wrapper.get('[data-testid="clean-job"] .el-button').trigger('click'); await flushPromises()
  job = { job_id: 'second-job', kind: 'clean', status: 'running', done: 1, total: 9, retry_count: 0 }
  await click('clean-run')
  release({ columns: ['commit_hash'], preview: [{ commit_hash: 'stale' }] })
  await flushPromises()
  expect(last('/jobs/second-job')).toBeDefined()
  expect(wrapper.find('[data-testid="clean-preview"]').exists()).toBe(false)
})
it('keeps draft on backend validation errors', async () => {
  replies['/clean/run'] = [{ code: 40001, message: '非法时间' }]
  await open(); await upload(); await click('clean-run')
  expect(wrapper.text()).toContain('非法时间')
  expect(wrapper.text()).toContain('commits.csv')
})
it('retries original job without sending updated form', async () => {
  job.status = 'failed'; job.error_log = 'failed'
  await open(); await upload(); await click('clean-run'); await click('clean-retry')
  expect(last('/jobs/test-job/retry')).toBeDefined()
  expect(calls.filter(call => call.url === '/clean/run')).toHaveLength(1)
})
it('cancels running job and disables a second run', async () => {
  job.status = 'running'
  await open(); await upload(); await click('clean-run')
  expect(wrapper.get('[data-testid="clean-run"]').attributes('disabled')).toBeDefined()
  await click('clean-cancel')
  expect(last('/jobs/test-job/cancel')).toBeDefined()
})
it('saves a reusable template without launching a job', async () => {
  await open(); await wrapper.get('#clean-template-name').setValue('default chain'); await click('clean-save-template')
  expect(JSON.parse(last('/config/clean.chain_templates').data).value['default chain'].steps).toHaveLength(9)
  expect(last('/clean/run')).toBeUndefined()
})
it('restores template steps with omitted enabled and params using server defaults', async () => {
  configuration.items = [{ config_key: 'clean.chain_templates', value: { minimal: { steps: [{ op: 'feature_align' }, { op: 'time_split' }], features: ['ns'], seed: 11 } } }]
  await open(); await wrapper.get('#clean-template').setValue('minimal')
  expect(wrapper.get('#clean-enabled-time_split').element.checked).toBe(true)
  expect(wrapper.get('#clean-param-time_split-ratio').element.value).toBe('0.7')
})
it('inherits a selected template top-level split ratio without resetting it', async () => {
  configuration.items = [{ config_key: 'clean.chain_templates', value: { chronological: { steps: [{ op: 'feature_align' }, { op: 'time_split' }], split_ratio: 0.8 } } }]
  await open(); await upload(); await wrapper.get('#clean-template').setValue('chronological')
  expect(wrapper.get('#clean-param-time_split-ratio').element.value).toBe('0.8')
  await click('clean-run')
  expect(JSON.parse(last('/clean/run').data.get('config')).steps.find(step => step.op === 'time_split').params.ratio).toBe(0.8)
})
it('loads collect artifact and same-stem manifest as ordinary uploaded files', async () => {
  replies['/jobs'] = [{ items: [{ job_id: 'collect-job', status: 'success', output_ref_json: { outputs: [{ name: 'collect_commits_collect-job.csv' }, { name: 'collect_commits_collect-job.manifest.json' }] } }], total: 1 }, { items: [], total: 0 }]
  await open(); await wrapper.get('#clean-source-artifact').setValue('collect-job/collect_commits_collect-job.csv'); await click('clean-use-artifact'); await click('clean-run')
  expect(last('/clean/run').data.getAll('files[]').map(file => file.name)).toEqual(['collect_commits_collect-job.csv', 'collect_commits_collect-job.manifest.json'])
})
