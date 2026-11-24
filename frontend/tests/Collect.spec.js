// AI-generated W3 tests, not yet human-reviewed.
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import { AxiosError } from 'axios'
import request from '../src/api/request'
import { configuration } from '../src/utils/thresholds'

const views = import.meta.glob('../src/views/*.vue')
const Collect = views['../src/views/Collect.vue'] ? (await views['../src/views/Collect.vue']()).default : undefined
const originalAdapter = request.defaults.adapter
const loadingDirective = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = loadingDirective })
let wrapper, calls, job, datasets, replies, fetchMock
const outputs = [
  { name: 'collect_commits_test-job.csv', sha256: 'a'.repeat(64), size_bytes: 100 },
  { name: 'collect_commits_test-job.xlsx', sha256: 'b'.repeat(64), size_bytes: 200 },
  { name: 'collect_commits_test-job.manifest.json', sha256: 'c'.repeat(64), size_bytes: 300 }
]
beforeEach(async () => {
  calls = []; replies = {}
  Object.assign(configuration, { items: [], schema: {}, ready: false, error: '', loading: false })
  job = { job_id: 'test-job', kind: 'collect', status: 'success', total: 5, done: 5, retry_count: 0,
    output_ref_json: { outputs, manifest_name: outputs[2].name, columns: ['commit_hash', 'is_bug_inducing'],
      summary: { rows: 2, positive_rows: 1, negative_rows: 0, unlabeled_rows: 1, head_hash: 'a'.repeat(40) } } }
  datasets = { items: [], total: 0, page: 1, size: 20 }
  request.defaults.adapter = async cfg => {
    calls.push(cfg)
    const data = replies[cfg.url]?.shift() ?? (cfg.url === '/datasets' ? datasets
      : cfg.url === '/jobs' ? { items: [], total: 0 } : cfg.url === '/collect/run' ? { job_id: 'test-job', status: 'queued' }
        : cfg.url === '/collect/preview/test-job' ? { columns: ['commit_hash', 'is_bug_inducing'], preview: [{ commit_hash: 'a'.repeat(40), is_bug_inducing: null }] }
          : cfg.url.endsWith('/retry') ? { job_id: 'test-job', status: 'queued', retry_count: 1 }
            : cfg.url.endsWith('/cancel') ? { job_id: 'test-job', status: 'cancelled' }
              : cfg.url === '/storage/import' ? { items: [{ status: 'success', inserted: 2, unchanged: 0, rejected: 0 }], summary: { inserted: 2, unchanged: 0, rejected: 0 } } : job)
    const response = { config: cfg, headers: {}, status: data?.code ? 400 : 200, data: data?.code ? data : { code: 0, data } }
    if (data?.code) throw new AxiosError('failed', 'ERR_BAD_RESPONSE', cfg, null, response)
    return response
  }
  fetchMock = vi.fn().mockResolvedValue({ ok: true, blob: async () => new Blob(['real server response']) })
  vi.stubGlobal('fetch', fetchMock)
  class TestURL extends URL {}
  Object.assign(TestURL, { createObjectURL: vi.fn(() => 'blob:collect-test'), revokeObjectURL: vi.fn() })
  vi.stubGlobal('URL', TestURL)
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  const stores = import.meta.glob('../src/utils/collect.js')
  if (stores['../src/utils/collect.js']) {
    const { collection } = await stores['../src/utils/collect.js']()
    Object.assign(collection, { job: null, preview: null, request: null })
  }
})
afterEach(() => {
  wrapper?.unmount(); document.body.innerHTML = ''
  request.defaults.adapter = originalAdapter
  vi.restoreAllMocks(); vi.unstubAllGlobals()
})
async function open() {
  expect(Collect, 'the real collect view must exist').toBeDefined()
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/collect', component: Collect }, { path: '/storage', component: { template: '<div>storage</div>' } }] })
  await router.push('/collect'); await router.isReady()
  wrapper = mount(Collect, { attachTo: document.body, global: { plugins: [ElementPlus, router] } })
  await flushPromises()
}
async function configure() {
  await wrapper.get('#collect-repo').setValue('/allowed/repo')
  await wrapper.get('#collect-name').setValue('AI fixture')
}
async function click(id) { await wrapper.get(`[data-testid="${id}"]`).trigger('click'); await flushPromises() }
const last = url => calls.filter(call => call.url === url).at(-1)

describe('independent collection tool', () => {
  it('wires the real collect route', async () => {
    const router = (await import('../src/router')).default
    expect(router.options.routes.find(route => route.path === '/collect')?.component).toBe(Collect)
  })
  it('has two local tabs and does not require registered datasets', async () => {
    await open()
    expect(wrapper.findAll('[data-testid="collect-tabs"] > .el-tabs__header [role="tab"]').map(tab => tab.text())).toEqual(['收集工具台', '已收集数据集'])
    await configure(); await click('collect-run')
    const config = JSON.parse(last('/collect/run').data.get('config'))
    expect(config.repo_source).toBe('/allowed/repo')
    expect(config.dataset_name).toBe('AI fixture')
    expect(last('/storage/import')).toBeUndefined()
  })
  it('restores persisted default branch and mode without running a task', async () => {
    configuration.items = [{ config_key: 'page_prefs', value: { collect_branch: 'release/main', collect_mode: 'full' } }]
    await open()
    expect(wrapper.get('#collect-branch').element.value).toBe('release/main')
    expect(wrapper.get('#collect-mode').element.value).toBe('full')
    expect(last('/collect/run')).toBeUndefined()
  })
  it('explicitly saves only branch and mode while preserving other page preferences', async () => {
    configuration.items = [{ config_key: 'page_prefs', value: { page_size: 50 } }]
    const prefs = { page_size: 50, collect_branch: 'main', collect_mode: 'full' }
    replies['/config'] = [{ schema: { risk_high_threshold: {}, risk_mid_threshold: {}, page_prefs: {} }, items: [
      { config_key: 'risk_high_threshold', value: 0.7 }, { config_key: 'risk_mid_threshold', value: 0.3 },
      { config_key: 'page_prefs', value: prefs }
    ] }]
    await open()
    await wrapper.get('#collect-branch').setValue('main')
    await wrapper.get('#collect-mode').setValue('full')
    await click('collect-save-defaults')
    expect(JSON.parse(last('/config/page_prefs').data).value).toEqual(prefs)
    expect(last('/collect/run')).toBeUndefined()
    expect(wrapper.text()).toContain('页面默认值已保存')
  })
  it('rejects an obviously out-of-root local path before posting a job', async () => {
    configuration.items = [{ config_key: 'collect.allow_roots', value: ['/allowed'] }]
    await open(); await configure()
    await wrapper.get('#collect-repo').setValue('/outside/repo')
    await click('collect-run')
    expect(last('/collect/run')).toBeUndefined()
    expect(wrapper.text()).toContain('允许根目录')
  })
  it('rejects a non-whitelisted URL protocol before posting a job', async () => {
    configuration.items = [{ config_key: 'collect.protocol_whitelist', value: ['https'] }]
    await open(); await configure()
    await wrapper.get('#collect-repo').setValue('file:///allowed/repo')
    await click('collect-run')
    expect(last('/collect/run')).toBeUndefined()
    expect(wrapper.text()).toContain('协议')
  })
  it('retains missing-field drafts without sending a run', async () => {
    await open(); await wrapper.get('#collect-name').setValue('keep draft'); await click('collect-run')
    expect(last('/collect/run')).toBeUndefined()
    expect(wrapper.get('#collect-name').element.value).toBe('keep draft')
    expect(wrapper.text()).toContain('仓库')
  })
  it('preserves the optional CSV/XLSX File and sends files[]', async () => {
    await open(); await configure()
    const input = wrapper.get('#collect-files')
    const file = new File(['commit_hash\n' + 'a'.repeat(40)], 'hashes.csv')
    Object.defineProperty(input.element, 'files', { configurable: true, value: [file] })
    await input.trigger('change'); await click('collect-run')
    expect(last('/collect/run').data.getAll('files[]')[0].name).toBe(file.name)
  })
  it('shows live job state and NULL labels, not zero', async () => {
    await open(); await configure(); await click('collect-run')
    expect(wrapper.get('[data-testid="collect-job"]').text()).toContain('成功')
    expect(wrapper.get('[data-testid="collect-preview"]').text()).toContain('未打标')
    expect(wrapper.text()).toContain('a'.repeat(40))
    expect(last('/collect/preview/test-job')).toBeDefined()
  })
  it('downloads actual registered artifacts with authenticated fetch and URL cleanup', async () => {
    await open(); await configure(); await click('collect-run'); await click('collect-download-csv')
    expect(fetchMock.mock.calls[0][0]).toBe('/api/collect/outputs/test-job/' + outputs[0].name)
    expect(fetchMock.mock.calls[0][1].headers).toHaveProperty('X-API-Key')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:collect-test')
  })
  it('imports CSV plus its matching manifest only after explicit action', async () => {
    await open(); await configure(); await click('collect-run')
    expect(last('/storage/import')).toBeUndefined()
    await click('collect-import')
    const form = last('/storage/import').data
    expect(form.getAll('files[]').map(file => file.name)).toEqual([outputs[0].name, outputs[2].name])
    expect(JSON.parse(form.get('config')).create_dataset).toEqual({ name: 'AI fixture', repo_source: '/allowed/repo', head_hash: 'a'.repeat(40) })
    expect(wrapper.text()).toContain('提交与数据集已入库')
  })
  it('keeps drafts and displays backend validation errors', async () => {
    replies['/collect/run'] = [{ code: 40001, message: '路径越界', data: null }]
    await open(); await configure(); await click('collect-run')
    expect(wrapper.text()).toContain('路径越界')
    expect(wrapper.get('#collect-repo').element.value).toBe('/allowed/repo')
  })
  it('retries a failed job using its ID, not changed form config', async () => {
    job.status = 'failed'; job.error_log = 'git failed'
    await open(); await configure(); await click('collect-run')
    await wrapper.get('#collect-repo').setValue('/another/repo')
    await click('collect-retry')
    expect(last('/jobs/test-job/retry')).toBeDefined()
    expect(calls.filter(call => call.url === '/collect/run')).toHaveLength(1)
  })
  it('can cancel queued/running jobs', async () => {
    job.status = 'running'; job.done = 1
    await open(); await configure(); await click('collect-run'); await click('collect-cancel')
    expect(last('/jobs/test-job/cancel')).toBeDefined()
  })
  it('keeps task progress across view unmounts', async () => {
    job.status = 'running'; job.done = 2
    await open(); await configure(); await click('collect-run'); wrapper.unmount()
    await open()
    expect(wrapper.get('[data-testid="collect-job"]').text()).toContain('test-job')
  })
  it('reads registered dataset counts and members without triggering collection', async () => {
    datasets = { items: [{ dataset_id: 'dataset1', name: '导入版本', repo_source: 'repo', sample_count: 2, pos_count: 1, neg_count: 0, status: 'ready' }], total: 1 }
    await open()
    expect(wrapper.text()).toContain('导入版本')
    expect(last('/collect/run')).toBeUndefined()
  })
  it('renders actual dataset member labels and flat feature columns', async () => {
    datasets = { items: [{ dataset_id: 'dataset1', name: '导入版本', repo_source: 'repo', sample_count: 3, pos_count: 1, neg_count: 1, status: 'ready' }], total: 1 }
    replies['/datasets/dataset1/commits'] = [{ total: 3, items: [
      { commit_hash: 'a', is_bug_inducing: 1, is_test: 0, ns: '0.0000000000', la: '-1.0986122887' },
      { commit_hash: 'b', is_bug_inducing: 0, is_test: 1, ns: '0.6931471806' },
      { commit_hash: 'c', is_bug_inducing: null, is_test: 1, ns: '0.0000000000' }
    ] }]
    await open()
    const button = wrapper.findAll('.dataset-table .el-button').find(x => x.text() === '查看')
    await button.trigger('click'); await flushPromises()
    const rows = [...document.querySelectorAll('.el-dialog .el-table__body tr')]
    expect(rows).toHaveLength(3)
    expect(rows.map(row => row.querySelectorAll('td')[3].textContent.trim())).toEqual(['1', '0', '未打标'])
    expect(rows[0].textContent).toContain('ns')
    expect(rows[0].textContent).toContain('-1.0986122887')
  })
  it('disables output downloads after a binary authentication failure', async () => {
    await open(); await configure(); await click('collect-run')
    fetchMock.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ code: 40100, message: 'invalid key' }) })
    await click('collect-download-csv')
    expect(wrapper.get('[data-testid="collect-download-csv"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('鉴权失败')
  })
  it('keeps a running task visible instead of replacing it with a second run', async () => {
    job.status = 'running'; job.done = 1
    await open(); await configure(); await click('collect-run')
    expect(wrapper.get('[data-testid="collect-run"]').attributes('disabled')).toBeDefined()
  })
  it('does not fabricate success when an import contains rejected files', async () => {
    replies['/storage/import'] = [{ items: [{ status: 'rejected', errors: ['invalid version'] }], summary: { rejected: 1, inserted: 0 } }]
    await open(); await configure(); await click('collect-run'); await click('collect-import')
    expect(wrapper.text()).not.toContain('提交与数据集已入库')
    expect(wrapper.text()).toContain('拒绝')
  })
})
