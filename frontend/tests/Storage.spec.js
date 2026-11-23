// All tests in this file are AI-generated and unreviewed; no human review is claimed.
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { AxiosError } from 'axios'
import ElementPlus from 'element-plus'
import request from '../src/api/request'
import { configuration } from '../src/utils/thresholds'
import App from '../src/App.vue'

const views = import.meta.glob('../src/views/*.vue')
const Storage = views['../src/views/Storage.vue'] ? (await views['../src/views/Storage.vue']()).default : undefined
const loading = config.global.directives.loading
const originalAdapter = request.defaults.adapter
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = loading })
let wrapper, router, calls, tables, datasets, importResult, exportResult, members, replies, fetchMock
const dataset = { dataset_id: 'dataset/real', name: '实际版本', repo_source: 'https://example.test/repo', branch: 'main', head_hash: 'abc123', sample_count: 10, pos_count: 2, neg_count: 3, status: 'ready', created_at: '2026-11-21T12:00:00Z' }
function batch(format = 'csv', id = 'batch/1') {
  return { job_id: id, table: 'commit', format, outputs: [{ name: `commits.${format}`, sha256: 'a'.repeat(64), size_bytes: 123 }, { name: 'commits.manifest.json', sha256: 'b'.repeat(64), size_bytes: 456 }], manifest_name: 'commits.manifest.json', columns: ['commit_hash', 'label', 'risk_score'], preview: [{ commit_hash: 'abc', label: null, risk_score: null }], row_count: 1, total: 31 }
}
function failure(status, code, message) { return { status, code, message } }
beforeEach(() => {
  vi.restoreAllMocks()
  vi.stubEnv('VITE_API_KEY', 'test-token-not-a-real-secret')
  calls = []
  replies = {}
  tables = { items: [{ name: 'commit', columns: ['commit_hash', 'message'], filters: ['dataset_id', 'start_time', 'end_time'] }, { name: 'server_new_table', columns: ['name'], filters: ['model_name'] }] }
  datasets = { total: 41, page: 1, size: 20, items: [structuredClone(dataset), { ...dataset, dataset_id: 'not-ready', name: '未就绪版本', status: 'collecting' }] }
  importResult = { items: [{ name: 'commits.csv', schema: 'commits', target_tables: ['commit', 'commit_feature'], status: 'success', inserted: 3, updated: 1, unchanged: 2, rejected: 0, errors: [] }], summary: { inserted: 3, updated: 1, unchanged: 2, rejected: 0 } }
  exportResult = batch()
  members = { total: 24, page: 1, size: 20, items: [{ commit_hash: 'deadbeef', committed_at: '2026-11-20T10:00:00Z', message: '真实提交', label: null, is_test: 1, features: { ns: 0.2 } }] }
  request.defaults.adapter = async (cfg) => {
    calls.push(cfg)
    const queued = replies[cfg.url]?.shift()
    const data = queued ?? (cfg.url === '/storage/tables' ? tables : cfg.url === '/datasets' ? datasets : cfg.url === '/storage/import' ? importResult : cfg.url === '/storage/export' ? exportResult : cfg.url.includes('/commits') ? members : cfg.url === '/config' ? configResponse() : undefined)
    const response = { config: cfg, headers: {}, status: data?.status || 200, statusText: '', data: data?.code ? { code: data.code, message: data.message, error: data.error, data: null } : { code: 0, message: 'ok', data } }
    if (response.status >= 400) throw new AxiosError('HTTP failed', 'ERR_BAD_RESPONSE', cfg, null, response)
    return response
  }
  fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, blob: async () => new Blob(['server file']) })
  vi.stubGlobal('fetch', fetchMock)
  class TestURL extends URL {}
  Object.assign(TestURL, { createObjectURL: vi.fn(() => 'blob:test'), revokeObjectURL: vi.fn() })
  vi.stubGlobal('URL', TestURL)
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  Object.assign(configuration, { ready: true, loading: false, error: '', items: [], schema: {} })
})
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
  request.defaults.adapter = originalAdapter
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})
function configResponse() {
  return { schema: { risk_high_threshold: { label: '高风险阈值', value_type: 'float', group: 'global' }, risk_mid_threshold: { label: '中风险阈值', value_type: 'float', group: 'global' } }, items: [{ config_key: 'risk_high_threshold', value: 0.7, source: 'factory' }, { config_key: 'risk_mid_threshold', value: 0.3, source: 'factory' }] }
}
async function open(path = '/storage', app = false) {
  expect(Storage, 'W2 real storage business view must exist').toBeDefined()
  const actualRouter = (await import('../src/router')).default
  router = createRouter({ history: createMemoryHistory(), routes: actualRouter.options.routes })
  await router.push(path)
  await router.isReady()
  wrapper = mount(app ? App : Storage, { attachTo: document.body, global: { plugins: [ElementPlus, router] } })
  await flushPromises()
}
async function click(id) { await wrapper.get(`[data-testid="${id}"]`).trigger('click'); await flushPromises() }
async function upload(names = ['commits.csv', 'commits.manifest.json']) {
  const input = wrapper.get('[data-testid="import-files"]')
  Object.defineProperty(input.element, 'files', { configurable: true, value: names.map(name => new File([name.endsWith('.json') ? '{"config":{"feature_version":"verified-version"}}' : 'commit_hash,message\nabc,test'], name)) })
  await input.trigger('change')
}
async function select(id, label) {
  await wrapper.get(`[data-testid="${id}"] .el-select`).trigger('click')
  await flushPromises()
  const listId = wrapper.get(`[data-testid="${id}"] input[aria-controls]`).attributes('aria-controls')
  const choices = Array.from(document.getElementById(listId).querySelectorAll('[role="option"]')).filter(node => node.textContent.trim() === label)
  expect(choices.length, `option ${label}`).toBeGreaterThan(0)
  choices[0].click()
  await flushPromises()
}
const last = url => calls.filter(call => call.url === url).at(-1)
const rows = id => wrapper.get(`[data-testid="${id}"]`).findAll('.el-table__body tr')

describe('W2 storage business actions with HTTP mocks', () => {
  it('loads real metadata and dataset statistics, with exactly two local tabs and no extra navigation', async () => {
    await open('/storage', true)
    expect(calls.some(call => call.url === '/storage/tables')).toBe(true)
    expect(last('/datasets').params).toEqual({ page: 1, size: 20 })
    expect(wrapper.findAll('.menu [role="menuitem"]').map(item => item.text())).toEqual(['数据管理', '收集', '清洗', '训练', '预测', '评估', '解释', '定位及修复'])
    expect(wrapper.findAll('[data-testid="storage-tabs"] > .el-tabs__header [role="tab"]').map(tab => tab.text())).toEqual(['数据导入导出', '用户配置'])
    const row = rows('datasets')[0].text()
    for (const value of ['实际版本', 'dataset/real', 'main', 'abc123', '10', '2', '3', '5', 'ready', dataset.created_at]) expect(row).toContain(value)
    await select('export-table', 'server_new_table')
    expect(wrapper.find('[data-testid="filter-model_name"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="filter-dataset_id"]').exists()).toBe(false)
  })
  it('uploads multiple CSV and companion manifest files with only the explicit create config', async () => {
    await open()
    await upload()
    await wrapper.get('[data-testid="dataset-name"] input').setValue('新版本')
    await wrapper.get('[data-testid="repo-source"] input').setValue('https://example.test/new')
    await click('submit-import')
    const form = last('/storage/import').data
    expect(form).toBeInstanceOf(FormData)
    expect(form.getAll('files[]').map(file => file.name)).toEqual(['commits.csv', 'commits.manifest.json'])
    expect(JSON.parse(form.get('config'))).toEqual({ create_dataset: { name: '新版本', repo_source: 'https://example.test/new' } })
    expect(wrapper.text()).toContain('导入请求已完成')
    expect(rows('import-results')[0].text()).toContain('commit_feature')
    expect(wrapper.text()).toContain('unchanged')
    expect(wrapper.text()).toContain('rejected')
    expect(wrapper.text()).not.toContain('skipped')
  })
  it('imports independently of an empty dataset database and never invents a feature version', async () => {
    datasets = { total: 0, page: 1, size: 20, items: [] }
    await open()
    expect(wrapper.text()).toContain('上传 commits.csv')
    await upload(['predictions.csv'])
    await click('submit-import')
    expect(JSON.parse(last('/storage/import').data.get('config'))).toEqual({})
    expect(wrapper.text()).toContain('manifest.config.feature_version')
    expect(wrapper.text()).not.toContain('v1')
  })
  it('uses an actual ready dataset ID without sending simultaneous create_dataset', async () => {
    await open()
    await select('import-dataset', '实际版本 · dataset/real')
    await upload()
    await click('submit-import')
    expect(JSON.parse(last('/storage/import').data.get('config'))).toEqual({ dataset_id: 'dataset/real' })
  })
  it('rejects incomplete dataset creation locally without losing the draft', async () => {
    await open()
    await upload()
    await wrapper.get('[data-testid="dataset-name"] input').setValue('只有名称')
    await click('submit-import')
    expect(last('/storage/import')).toBeUndefined()
    expect(wrapper.text()).toContain('名称和来源仓库')
    expect(wrapper.get('[data-testid="dataset-name"] input').element.value).toBe('只有名称')
  })
  it('shows rejected files in a mixed HTTP 200 result instead of blanket success', async () => {
    importResult.items.push({ name: 'bad.csv', schema: null, target_tables: [], status: 'rejected', inserted: 0, updated: 0, unchanged: 0, rejected: 2, errors: ['缺少合法 schema'] })
    await open()
    await upload(['commits.csv', 'bad.csv'])
    await click('submit-import')
    expect(rows('import-results')[1].text()).toContain('rejected')
    expect(rows('import-results')[1].text()).toContain('缺少合法 schema')
    expect(wrapper.text()).toContain('存在拒绝项')
  })
  it('retains selected files and creation drafts on all-rejected 40001', async () => {
    replies['/storage/import'] = [failure(400, 40001, 'manifest.config.feature_version 缺失')]
    await open()
    await upload()
    await wrapper.get('[data-testid="dataset-name"] input').setValue('保留草稿')
    await wrapper.get('[data-testid="repo-source"] input').setValue('repo')
    await click('submit-import')
    expect(wrapper.text()).toContain('manifest.config.feature_version 缺失')
    expect(wrapper.get('[data-testid="selected-files"]').text()).toContain('commits.csv')
    expect(wrapper.get('[data-testid="dataset-name"] input').element.value).toBe('保留草稿')
    expect(wrapper.text()).not.toContain('导入请求已完成')
    await click('submit-import')
    expect(calls.filter(call => call.url === '/storage/import')).toHaveLength(2)
  })
  it.each([{ summary: {} }, { items: [], summary: {} }, { items: [{ name: 'x', status: 'success' }], summary: {} }])('does not fabricate import success from malformed/no-result responses %j', async (bad) => {
    importResult = bad
    await open()
    await upload()
    await click('submit-import')
    expect(wrapper.text()).toContain('导入响应不完整')
    expect(wrapper.text()).not.toContain('导入请求已完成')
    expect(wrapper.get('[data-testid="selected-files"]').text()).toContain('commits.csv')
  })
  it('previews with limit=20 and keeps NULL labels and other NULL values distinct from zero', async () => {
    await open()
    await click('preview-export')
    expect(last('/storage/export').params).toEqual({ table: 'commit', format: 'csv', limit: 20 })
    const cells = wrapper.get('[data-testid="export-preview"] tbody tr').findAll('td')
    expect(cells.map(cell => cell.text())).toEqual(['abc', '未打标', ''])
    expect(wrapper.text()).toContain('预览批次')
    expect(wrapper.text()).toContain('不是完整文件')
    expect(wrapper.text()).toContain('a'.repeat(64))
    expect(wrapper.text()).toContain('31')
    expect(fetchMock).not.toHaveBeenCalled()
  })
  it('full CSV download creates a new export without limit and authenticated encoded binary fetch', async () => {
    await open()
    await click('preview-export')
    exportResult = batch('csv', 'full/2')
    await click('download-csv')
    expect(last('/storage/export').params).toEqual({ table: 'commit', format: 'csv' })
    expect(fetchMock).toHaveBeenCalledWith('/api/storage/outputs/full%2F2/commits.csv', { headers: { 'X-API-Key': 'test-token-not-a-real-secret' } })
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test')
    expect(wrapper.text()).toContain('完整导出批次')
  })
  it('downloads XLSX generated by the server, not browser-converted CSV', async () => {
    exportResult = batch('xlsx', 'xlsx-batch')
    await open()
    await click('download-xlsx')
    expect(last('/storage/export').params).toEqual({ table: 'commit', format: 'xlsx' })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/storage/outputs/xlsx-batch/commits.xlsx')
  })
  it('downloads manifest only from the currently completed batch without a new export request', async () => {
    await open()
    expect(wrapper.get('[data-testid="download-manifest"]').attributes('disabled')).toBeDefined()
    await click('preview-export')
    await click('download-manifest')
    expect(calls.filter(call => call.url === '/storage/export')).toHaveLength(1)
    expect(fetchMock.mock.calls[0][0]).toBe('/api/storage/outputs/batch%2F1/commits.manifest.json')
  })
  it('sends only filters permitted by table metadata and clears hidden filters after switching tables', async () => {
    await open()
    await wrapper.get('[data-testid="filter-start_time"] input').setValue('2026-11-01T00:00:00Z')
    await click('preview-export')
    expect(last('/storage/export').params.start_time).toBe('2026-11-01T00:00:00Z')
    await select('export-table', 'server_new_table')
    exportResult = { ...batch(), table: 'server_new_table' }
    await wrapper.get('[data-testid="filter-model_name"] input').setValue('actual-model')
    await click('preview-export')
    expect(last('/storage/export').params).toEqual({ table: 'server_new_table', format: 'csv', model_name: 'actual-model', limit: 20 })
  })
  it('reads members with correct encoded ID, actual pagination and optional feature values', async () => {
    await open()
    await rows('datasets')[0].get('[data-testid="view-members"]').trigger('click')
    await flushPromises()
    expect(last('/datasets/dataset%2Freal/commits').params).toEqual({ page: 1, size: 20, with_features: 1 })
    expect(document.body.textContent).toContain('deadbeef')
    expect(document.body.textContent).toContain('未打标')
    expect(document.body.textContent).toContain('0.2')
    document.querySelector('[data-testid="member-pagination"] .btn-next').click()
    await flushPromises()
    expect(last('/datasets/dataset%2Freal/commits').params.page).toBe(2)
  })
  it('exports the selected dataset as a raw commit table with no feature-schema claim', async () => {
    await open()
    await rows('datasets')[0].get('[data-testid="export-dataset"]').trigger('click')
    await flushPromises()
    expect(last('/storage/export').params).toEqual({ table: 'commit', format: 'csv', dataset_id: 'dataset/real' })
    expect(wrapper.text()).toContain('提交表导出')
    expect(wrapper.text()).toContain('不包含 14 维特征交换列')
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
  it('paginates datasets using backend total', async () => {
    await open()
    await wrapper.get('[data-testid="dataset-pagination"] .btn-next').trigger('click')
    await flushPromises()
    expect(last('/datasets').params).toEqual({ page: 2, size: 20 })
    expect(wrapper.get('[data-testid="dataset-pagination"]').text()).toContain('41')
  })
  it('metadata failure disables only the table picker and can retry while configuration remains usable', async () => {
    replies['/storage/tables'] = [failure(500, 50000, 'private SQL path must not appear')]
    await open()
    expect(wrapper.text()).not.toContain('private SQL path')
    expect(wrapper.get('[data-testid="export-table"] input').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-testid="submit-import"]').attributes('disabled')).toBeDefined()
    await upload()
    expect(wrapper.get('[data-testid="submit-import"]').attributes('disabled')).toBeUndefined()
    await click('retry-tables')
    expect(wrapper.get('[data-testid="export-table"] input').attributes('disabled')).toBeUndefined()
    await wrapper.get('[role="tab"][id$="-config"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.section).toBe('config')
    expect(wrapper.find('[data-config-key="risk_high_threshold"]').exists()).toBe(true)
  })
  it('failed dataset refresh retains previous rows, exposes retry, and does not hide import results', async () => {
    await open()
    replies['/datasets'] = [failure(500, 50000, 'internal DB detail')]
    await upload()
    await click('submit-import')
    expect(rows('datasets')[0].text()).toContain('实际版本')
    expect(wrapper.text()).toContain('导入请求已完成')
    expect(wrapper.find('[data-testid="retry-datasets"]').exists()).toBe(true)
    await click('retry-datasets')
    expect(wrapper.find('[data-testid="retry-datasets"]').exists()).toBe(false)
  })
  it('invalid metadata and datasets are visible read failures rather than invented empty records', async () => {
    tables = { items: [{ name: 'bad' }] }
    datasets = { items: [] }
    await open()
    expect(wrapper.text()).toContain('表元数据响应不完整')
    expect(wrapper.text()).toContain('数据集响应不完整')
    expect(wrapper.text()).not.toContain('上传 commits.csv')
  })
  it('failed exports preserve a previous preview and retry the failed action without downloading partial files', async () => {
    await open()
    await click('preview-export')
    replies['/storage/export'] = [failure(500, 50000, 'secret internal path')]
    await click('download-csv')
    expect(wrapper.get('[data-testid="export-preview"]').text()).toContain('abc')
    expect(fetchMock).not.toHaveBeenCalled()
    await click('retry-export')
    expect(last('/storage/export').params.limit).toBeUndefined()
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
  it('malformed export responses cannot be downloaded as successful complete files', async () => {
    exportResult = { job_id: 'broken', outputs: [] }
    await open()
    await click('download-csv')
    expect(wrapper.text()).toContain('导出响应不完整')
    expect(fetchMock).not.toHaveBeenCalled()
  })
  it('binary error JSON retains 40001 detail and never creates a blob download', async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 400, json: async () => ({ code: 40001, message: '下载名称不合法' }) })
    await open()
    await click('download-csv')
    expect(wrapper.text()).toContain('下载名称不合法')
    expect(URL.createObjectURL).not.toHaveBeenCalled()
  })
  it('auth disables the failed import independently and retains inputs without exposing a key editor', async () => {
    replies['/storage/import'] = [failure(401, 40100, 'invalid key')]
    await open()
    await upload()
    await click('submit-import')
    expect(wrapper.get('[data-testid="submit-import"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-testid="download-csv"]').attributes('disabled')).toBeUndefined()
    expect(wrapper.get('[data-testid="selected-files"]').text()).toContain('commits.csv')
    expect(wrapper.html()).not.toContain('test-token-not-a-real-secret')
    expect(wrapper.find('input[type="password"]').exists()).toBe(false)
  })
  it('binary authentication failure disables only export actions', async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ code: 40100, message: 'unauthorized' }) })
    await open()
    await click('download-csv')
    expect(wrapper.get('[data-testid="download-csv"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-testid="retry-export"]').exists()).toBe(false)
    await upload()
    expect(wrapper.get('[data-testid="submit-import"]').attributes('disabled')).toBeUndefined()
  })
  it('keeps missing prediction labels blank and preserves genuine zero values', async () => {
    exportResult.columns = ['is_bug_inducing', 'predicted_label', 'risk_score', 'is_test']
    exportResult.preview = [{ is_bug_inducing: null, predicted_label: null, risk_score: 0, is_test: 0 }]
    await open()
    await click('preview-export')
    expect(wrapper.get('[data-testid="export-preview"] tbody tr').findAll('td').map(cell => cell.text())).toEqual(['未打标', '', '0', '0'])
  })
  it('shows a genuine empty export without fabricated records', async () => {
    exportResult = { ...batch(), preview: [], row_count: 0, total: 0 }
    await open()
    await click('preview-export')
    expect(wrapper.text()).toContain('当前查询没有可预览记录')
    expect(wrapper.find('[data-testid="export-preview"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('本批次 0 行')
  })
  it('preserves structured safe backend validation detail for rejected imports', async () => {
    replies['/storage/import'] = [{ ...failure(400, 40001, 'validation failed'), error: { detail: 'companion manifest checksum 不匹配' } }]
    await open()
    await upload()
    await click('submit-import')
    expect(wrapper.text()).toContain('companion manifest checksum 不匹配')
    expect(wrapper.text()).not.toContain('导入请求已完成')
  })
  it('initial dataset read failure retries independently of file import', async () => {
    replies['/datasets'] = [failure(500, 50000, 'private database detail')]
    await open()
    expect(wrapper.find('[data-testid="retry-datasets"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('private database detail')
    await upload()
    expect(wrapper.get('[data-testid="submit-import"]').attributes('disabled')).toBeUndefined()
    await click('retry-datasets')
    expect(rows('datasets')[0].text()).toContain('实际版本')
  })
  it('member read failures retain loaded members and expose a working retry', async () => {
    await open()
    await rows('datasets')[0].get('[data-testid="view-members"]').trigger('click')
    await flushPromises()
    replies['/datasets/dataset%2Freal/commits'] = [failure(500, 50000, 'private member path')]
    document.querySelector('[data-testid="member-pagination"] .btn-next').click()
    await flushPromises()
    expect(document.body.textContent).toContain('deadbeef')
    expect(document.body.textContent).not.toContain('private member path')
    const retry = Array.from(document.querySelectorAll('.el-dialog button')).find(button => button.textContent.trim() === '重试读取成员')
    expect(retry).toBeDefined()
    retry.click()
    await flushPromises()
    expect(calls.filter(call => call.url === '/datasets/dataset%2Freal/commits')).toHaveLength(3)
  })
  it('sync import loading has no fake progress and blocks duplicate submissions', async () => {
    await open()
    await upload()
    let release
    const pending = new Promise(resolve => { release = resolve })
    const adapter = request.defaults.adapter
    request.defaults.adapter = async cfg => {
      if (cfg.url === '/storage/import') await pending
      return adapter(cfg)
    }
    await wrapper.get('[data-testid="submit-import"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="submit-import"]').attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('正在等待后端同步校验及导入结果')
    expect(wrapper.find('[role="progressbar"]').exists()).toBe(false)
    release()
    await flushPromises()
    expect(calls.filter(call => call.url === '/storage/import')).toHaveLength(1)
    expect(wrapper.text()).toContain('导入请求已完成')
  })
  it('/settings redirects to the embedded original Settings view and returning to data removes section only', async () => {
    await open('/settings?keep=yes')
    expect(router.currentRoute.value.path).toBe('/storage')
    expect(router.currentRoute.value.query.section).toBe('config')
    expect(wrapper.get('[role="tab"][id$="-config"]').attributes('aria-selected')).toBe('true')
    expect(wrapper.find('[data-config-key="risk_high_threshold"]').exists()).toBe(true)
    await wrapper.get('[role="tab"][id$="-data"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query.section).toBeUndefined()
    expect(router.currentRoute.value.query.keep).toBe('yes')
    await router.push('/storage?section=config&keep=yes')
    await flushPromises()
    expect(wrapper.get('[role="tab"][id$="-config"]').attributes('aria-selected')).toBe('true')
  })
})
