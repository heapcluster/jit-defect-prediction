// AI-generated boundary tests; not human-reviewed.
import { afterAll, afterEach, beforeAll, beforeEach, expect, it, vi } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import { AxiosError } from 'axios'
import request from '../src/api/request'
import { configuration } from '../src/utils/thresholds'

const views = import.meta.glob('../src/views/*.vue')
const Localization = views['../src/views/Localization.vue'] ? (await views['../src/views/Localization.vue']()).default : undefined
const adapter = request.defaults.adapter, loading = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = loading })
let wrapper, calls, replies, metadata, accepted, evidence, fetchMock, sourceJobs
// Confirmed in backend/app/services/config_store.py; deliberately changed per-test to detect frontend defaults.
const weights = {
  file_types: { source: 1, other: 0.6, document: 0.4, test: 0.35, generated: 0.1 },
  change: { deleted: 2, modified: 1.5 }, hunk: 0.15,
  line_content: { empty: 0.1, comment: 0.15, import: 0.3, suspicious: 1.5, normal: 1 },
  line_path: { source: 1, other: 0.9, document: 0.55, test: 0.6, generated: 0.35 },
  mix: { base: 0.45, file: 0.35, hunk: 0.2 }
}
const suggestions = '# 定位建议\n## 1. 风险位置\nsrc/main.js:2\n## 2. 修复思路\n检查边界\n## 3. 验证步骤\n回归测试\n## 4. 证据与不足\nmissing_explanation'
const makeRow = (line = 2, suspicion = 0.8, hash = 'abc') => ({ commit_hash: hash, file_path: 'src/main.js', line_number: line, suspicion, rank: 1, evidence_json: JSON.stringify({ prediction: { risk_score: 0.91, model_name: 'm1', model_version: 'v1', feature_version: 'f1' }, explanation: { context: 'boundary explanation' }, hunk: '@@ original hunk', code: 'return unsafe()', history: ['past regression'], insufficiencies: ['missing_explanation'] }), level: 'line' })
function outputs(id) { return [
  { name: `localization_localization_${id}.csv`, sha256: 'csv-sha', size_bytes: 100 },
  { name: `localization_evidence_${id}.json`, sha256: 'json-sha', size_bytes: 200 },
  { name: `localization_suggestions_${id}.md`, sha256: 'md-sha', size_bytes: 300 }
] }
function successful(id = 'one') { return { job_id: id, status: 'success', outputs: outputs(id), summary: { commits: 1, localized_rows: 2, line_rows: 2, commit_rows: 0, insufficient_count: 1, truncated: false, suggestion_sources: ['template'], patch_reason: 'no_reliable_patch' }, localization: [makeRow()], suggestions } }
function deferred() { let resolve; const promise = new Promise(r => { resolve = r }); return { promise, resolve } }
function blobResponse(content) { return { ok: true, blob: async () => new Blob([content]) } }
function tree(hash = 'abc', path = '') { return { commit_hash: hash, path, entries: path ? [{ name: 'main.js', path: 'src/main.js', type: 'blob', size: 900, mode: '100644' }] : [{ name: 'src', path: 'src', type: 'tree' }, { name: 'main.js', path: 'src/main.js', type: 'blob' }], truncated: false, skipped: [] } }
beforeEach(() => {
  calls = []; replies = {}; sourceJobs = {}; accepted = successful()
  metadata = { items: [
    { config_key: 'risk_high_threshold', value: 0.7 }, { config_key: 'risk_mid_threshold', value: 0.4 },
    { config_key: 'collect.allow_roots', value: ['/allowed/repositories'] },
    { config_key: 'localization.weights', value: structuredClone(weights) },
    { config_key: 'localization.top_n', value: { files: 5, lines: 30 } },
    { config_key: 'localization.file_size_max', value: 1048576 },
    { config_key: 'localization.suggestion_sources', value: ['template'] }
  ], schema: { 'localization.suggestion_sources': { choices: ['template', 'llm', 'history'] } } }
  configuration.items = structuredClone(metadata.items); configuration.schema = metadata.schema
  configuration.ready = true; configuration.error = ''
  evidence = { rows: [makeRow(), makeRow(2, 0.6)], evidence: { abc: { diff: 'diff --git a/src/main.js b/src/main.js\n@@ -1 +1 @@\n-original\n+<script>unsafe()</script>', files: [{ path: 'src/main.js', selected_lines: [2], category: 'source', file_raw: 4, file_norm: 1, hunks: [{ header: '@@ original hunk' }] }], scores: { file: 1 }, predictions: [{ prediction: { risk_score: 0.91, model_name: 'm1', model_version: 'v1', feature_version: 'f1' }, explanation: { context: 'boundary explanation' }, history: ['past regression'], insufficiencies: ['missing_explanation'] }], insufficiencies: ['missing_explanation'] } }, summary: accepted.summary }
  request.defaults.adapter = async cfg => {
    calls.push(cfg)
    const value = await (replies[cfg.url]?.shift() ?? (cfg.url === '/config' ? metadata
      : cfg.url.startsWith('/config/') ? {}
        : cfg.url === '/datasets' ? { items: [{ dataset_id: 'dataset-one', name: 'Dataset', repo_source: '/dataset/repo' }] }
          : cfg.url === '/jobs' ? { items: sourceJobs[cfg.params.kind] || [] }
            : cfg.url === '/localize/run' ? accepted
              : cfg.url === '/source/tree' ? tree(cfg.params.commit_hash, cfg.params.path)
                : cfg.url === '/source/file' ? { commit_hash: cfg.params.commit_hash, path: cfg.params.path, status: 'ok', content: Array.from({ length: Math.min(200, 450 - cfg.params.start_line + 1) }, (_, i) => cfg.params.start_line + i === 2 ? '<script>unsafe()</script>' : `line ${cfg.params.start_line + i}`).join('\n'), start_line: cfg.params.start_line, end_line: Math.min(cfg.params.end_line, 450), total_lines: 450, size_bytes: 900, encoding: 'utf-8', reason: null } : {}))
    const response = { config: cfg, headers: {}, status: value?.code ? (value.code === 40100 ? 401 : 400) : 200, data: value?.code ? value : { code: 0, data: JSON.parse(JSON.stringify(value)) } }
    if (value?.code) throw new AxiosError('failed', 'ERR_BAD_RESPONSE', cfg, null, response)
    return response
  }
  fetchMock = vi.fn(async url => blobResponse(url.includes('localization_evidence_') ? JSON.stringify(evidence) : 'registered artifact'))
  vi.stubGlobal('fetch', fetchMock)
  class TestURL extends URL {}
  let next = 0
  Object.assign(TestURL, { createObjectURL: vi.fn(() => `blob:localization-${++next}`), revokeObjectURL: vi.fn() })
  vi.stubGlobal('URL', TestURL)
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
})
afterEach(() => {
  wrapper?.unmount(); wrapper = null; document.body.innerHTML = ''
  request.defaults.adapter = adapter; vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers()
})
async function open(query = '') {
  expect(Localization, 'real Localization.vue must exist').toBeDefined()
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/localization', component: Localization }] })
  await router.push(`/localization${query}`); await router.isReady()
  wrapper = mount(Localization, { attachTo: document.body, global: { plugins: [ElementPlus, router] } }); await flushPromises()
}
async function upload(names = ['pred.csv']) {
  const files = names.map(name => new File(['server parses §3.4 content, not browser'], name))
  const input = wrapper.get('#localization-files')
  Object.defineProperty(input.element, 'files', { configurable: true, value: files })
  await input.trigger('change'); return files
}
async function click(id) { await wrapper.get(`[data-testid="${id}"]`).trigger('click'); await flushPromises() }
const last = url => calls.filter(c => c.url === url).at(-1)
const payload = () => JSON.parse(last('/localize/run').data.get('config'))
async function ready(hash = '') { await wrapper.get('#localization-repo').setValue('/original/repo'); await wrapper.get('#localization-commit').setValue(hash); await upload() }
async function browse() { await wrapper.get('#localization-repo').setValue('/original/repo'); await wrapper.get('#localization-commit').setValue('abc'); await click('localization-source-browse') }
async function chooseFile() { await click('localization-entry-src/main.js') }

it('provides the real localization view', () => { expect(Localization, 'real Localization.vue must exist').toBeDefined() })
it('browses commit source before uploading with no localization call or HEAD fallback', async () => {
  await open(); expect(wrapper.get('#localization-source-browse').attributes('disabled')).toBeDefined()
  await browse(); await chooseFile()
  expect(last('/source/tree').params).toEqual({ repo_source: '/original/repo', commit_hash: 'abc', path: '' })
  expect(last('/source/file').params).toMatchObject({ commit_hash: 'abc', path: 'src/main.js', start_line: 1, end_line: 200 })
  expect(last('/localize/run')).toBeUndefined(); expect(wrapper.get('#localization-run').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-testid="localization-code"]').text()).toContain('<script>unsafe()</script>')
  expect(wrapper.find('[data-testid="localization-code"] script').exists()).toBe(false)
})
it('loads full server weights and route scope, posts files synchronously without job polls', async () => {
  configuration.items.find(i => i.config_key === 'localization.top_n').value = { files: 7, lines: 41 }
  configuration.items.find(i => i.config_key === 'localization.weights').value.mix.base = 0.72
  await open('?commit_hash=abc&model_name=route-model'); await wrapper.get('#localization-repo').setValue('/original/repo')
  const files = await upload(['pred.xlsx', 'explain.csv', 'pred.manifest.json']); await click('localization-run')
  expect(payload()).toEqual({ repo_source: '/original/repo', commit_hash: 'abc', model_name: 'route-model', weights: { ...weights, mix: { ...weights.mix, base: 0.72 } }, top_n: { files: 7, lines: 41 }, file_size_max: 1048576, suggestion_sources: ['template'], patch_preview: true, format: 'csv' })
  expect(last('/localize/run').data.getAll('files[]').map(f => f.name)).toEqual(files.map(f => f.name))
  expect(calls.filter(c => c.url === '/jobs').every(c => ['predict_batch', 'explain'].includes(c.params.kind) && c.params.size === 100)).toBe(true)
  expect(calls.some(c => /^\/jobs\//.test(c.url))).toBe(false)
  expect(wrapper.get('[data-testid="localization-result"]').text()).toContain('one')
  expect(wrapper.find('.el-progress').exists()).toBe(false)
})
it('dataset repository convenience never substitutes for a prediction file', async () => {
  await open(); await wrapper.get('#localization-dataset').setValue('dataset-one')
  expect(wrapper.get('#localization-repo').element.value).toBe('/dataset/repo')
  expect(wrapper.get('#localization-run').attributes('disabled')).toBeDefined()
  await upload(['explain.csv']); expect(wrapper.get('#localization-run').attributes('disabled')).toBeDefined()
  await upload(); await click('localization-run'); expect(payload().repo_source).toBe('/dataset/repo')
})
it('keeps arbitrary direct uploads as one prediction and one optional explanation', async () => {
  await open(); await wrapper.get('#localization-repo').setValue('/repo'); await upload(['arbitrary-one.csv', 'arbitrary-two.xlsx']); await click('localization-run')
  expect(last('/localize/run').data.getAll('files[]').map(f => f.name)).toEqual(['arbitrary-one.csv', 'arbitrary-two.xlsx'])
})
it('validates negative/nonfinite nested weights and positive bounded top N without losing drafts', async () => {
  await open(); await ready(); await wrapper.get('#localization-weights').setValue('{"mix":{"base":-1}}'); await click('localization-run')
  expect(last('/localize/run')).toBeUndefined(); expect(wrapper.text()).toContain('weights')
  await wrapper.get('#localization-weights').setValue('{"hunk":1e999}'); await click('localization-run'); expect(last('/localize/run')).toBeUndefined()
  await wrapper.get('#localization-weights').setValue('{"mix":{"base":0.25}}'); await wrapper.get('#localization-top-files').setValue('1001'); await click('localization-run')
  expect(last('/localize/run')).toBeUndefined()
  await wrapper.get('#localization-top-files').setValue('3'); await wrapper.get('#localization-format').setValue('xlsx'); await click('localization-run')
  expect(payload().weights).toEqual({ mix: { base: 0.25 } }); expect(payload().format).toBe('xlsx'); expect(wrapper.text()).toContain('pred.csv')
  expect(wrapper.text()).toContain('20'); expect(wrapper.text()).toContain('5000')
})
it('disables run on missing/null backend metadata and offers retry without fallback defaults', async () => {
  configuration.items.find(i => i.config_key === 'localization.weights').value = null
  await open(); await ready(); expect(wrapper.get('#localization-run').attributes('disabled')).toBeDefined()
  expect(wrapper.get('#localization-weights').element.value).toBe('')
  await click('localization-retry-metadata'); expect(wrapper.get('#localization-top-lines').element.value).toBe('30')
  await click('localization-run'); expect(last('/localize/run')).toBeDefined()
})
it('loads configuration when unavailable and preserves inputs on metadata HTTP errors', async () => {
  configuration.ready = false; replies['/config'] = [{ code: 50000, message: 'metadata unavailable' }]
  await open(); await ready(); expect(wrapper.get('#localization-run').attributes('disabled')).toBeDefined()
  await click('localization-retry-metadata'); expect(wrapper.text()).toContain('pred.csv'); expect(wrapper.text()).toContain('/allowed/repositories')
})
it('saves only business defaults with explicit PUT and full configuration reload, never runs', async () => {
  await open(); await wrapper.get('#localization-top-files').setValue('9'); await wrapper.get('#localization-source-history').setValue(true)
  await click('localization-save-defaults')
  expect(JSON.parse(last('/config/localization.top_n').data)).toEqual({ value: { files: 9, lines: 30 } })
  expect(JSON.parse(last('/config/localization.suggestion_sources').data)).toEqual({ value: ['template', 'history'] })
  expect(calls.filter(c => c.method === 'put').map(c => c.url).sort()).toEqual(['file_size_max', 'suggestion_sources', 'top_n', 'weights'].map(k => `/config/localization.${k}`).sort())
  expect(last('/config')).toBeDefined(); expect(last('/localize/run')).toBeUndefined()
})
it('retains submitted repository and actual result hash after draft changes, including page requests', async () => {
  await open(); await ready(); await click('localization-run'); await chooseFile()
  await wrapper.get('#localization-repo').setValue('/dirty/repo'); await wrapper.get('#localization-commit').setValue('dirty-ref')
  await click('localization-next-page')
  expect(last('/source/file').params).toMatchObject({ repo_source: '/original/repo', commit_hash: 'abc', start_line: 201, end_line: 400 })
  expect(wrapper.get('[data-testid="localization-source-version"]').text()).toContain('abc')
})
it('highlights the highest matching suspicion, rank and click-through raw risk/context, not line probability', async () => {
  await open(); await ready(); await click('localization-run'); await chooseFile()
  const highlight = wrapper.get('[data-testid="localization-line-2"] .suspicion-badge')
  expect(highlight.text()).toContain('0.800000'); expect(highlight.text()).toContain('1')
  expect(wrapper.get('[data-testid="localization-source-risk"]').text()).toContain('0.910000')
  await highlight.trigger('click'); await flushPromises()
  const pane = document.body.querySelector('[data-testid="localization-evidence-pane"]')
  for (const text of ['boundary explanation', 'past regression', 'missing_explanation', '@@ original hunk', '0.91', 'model_version']) expect(pane.textContent).toContain(text)
  expect(wrapper.text()).toContain('不是训练得到的行级概率')
})
it('uses complete evidence rows beyond twenty to retain highlights after pagination and jump', async () => {
  evidence.rows = [...Array.from({ length: 21 }, (_, i) => makeRow(i + 1)), makeRow(205, 0.95)]
  await open(); await ready(); await click('localization-run'); await chooseFile()
  expect(wrapper.findAll('[data-testid="localization-row"]')).toHaveLength(20)
  await click('localization-next-page'); expect(wrapper.get('[data-testid="localization-line-205"] .suspicion-badge').text()).toContain('0.950000')
  await wrapper.get('#localization-jump-line').setValue('205'); await click('localization-jump')
  expect(last('/source/file').params.start_line).toBe(201)
  await wrapper.get('#localization-jump-line').setValue('451'); const count = calls.length; await click('localization-jump'); expect(calls.length).toBe(count)
  expect(wrapper.text()).toContain('450'); await click('localization-prev-page'); expect(wrapper.find('[data-testid="localization-line-2"] .suspicion-badge').exists()).toBe(true)
})
it('shows only the original unified diff with literal escaping, never a suggested repair patch', async () => {
  await open(); await ready(); await click('localization-run'); await wrapper.get('#localization-source-mode').setValue('diff')
  expect(wrapper.get('[data-testid="localization-original-diff"]').text()).toBe(evidence.evidence.abc.diff)
  expect(wrapper.text()).toContain('原始提交 diff'); expect(wrapper.find('[data-testid="localization-original-diff"] script').exists()).toBe(false)
})
it('surfaces commit fallback, truncation and insufficiencies without inventing a line or patch', async () => {
  evidence.rows = [{ ...makeRow(), file_path: null, line_number: null, level: 'commit' }]
  accepted.localization = evidence.rows
  accepted.summary = { ...accepted.summary, commit_rows: 1, line_rows: 0, truncated: true }; evidence.summary = accepted.summary
  await open(); await ready(); await click('localization-run'); await chooseFile()
  expect(wrapper.get('[data-testid="localization-summary"]').text()).toContain('提交级回退')
  expect(wrapper.text()).toContain('截断'); expect(wrapper.text()).toContain('missing_explanation'); expect(wrapper.text()).toContain('no_reliable_patch')
  expect(wrapper.find('.suspicion-badge').exists()).toBe(false)
  expect(wrapper.findAll('[data-testid="localization-suggestion-part"]')).toHaveLength(4)
  expect(wrapper.get('[data-testid="localization-suggestions"]').text()).toContain('检查边界')
  for (const id of ['localization-import', 'localization-apply', 'localization-checkout', 'localization-commit', 'localization-pr']) expect(wrapper.find(`button[data-testid="${id}"]`).exists()).toBe(false)
  expect(wrapper.text()).not.toContain('12 表')
})
it.each(['binary', 'too_large', 'not_found'])('shows %s source reason with no fake content', async status => {
  replies['/source/file'] = [{ commit_hash: 'abc', path: 'src/main.js', status, content: null, total_lines: null, reason: `reason-${status}`, size_bytes: 999 }]
  await open(); await browse(); await chooseFile()
  expect(wrapper.get('[data-testid="localization-file-empty"]').text()).toContain(`reason-${status}`)
  expect(wrapper.find('[data-testid="localization-code"]').exists()).toBe(false); expect(wrapper.get('[data-testid="localization-result-empty"]').exists()).toBe(true)
})
it('navigates folders, parent and root with path substring search', async () => {
  await open(); await browse(); await click('localization-entry-src'); expect(last('/source/tree').params.path).toBe('src')
  await click('localization-tree-back'); expect(last('/source/tree').params.path).toBe('')
  await wrapper.get('#localization-source-search').setValue('main'); await click('localization-source-search')
  expect(last('/source/tree').params.search).toBe('main'); await click('localization-tree-root'); expect(last('/source/tree').params.path).toBe('')
})
it('downloads prediction/explanation artifacts and listed companions, replacing only the same role', async () => {
  sourceJobs = {
    predict_batch: [{ kind: 'predict_batch', job_id: 'pred-job', output_ref_json: { outputs: [{ name: 'predictions.csv' }, { name: 'predictions.manifest.json' }] } }],
    explain: [{ kind: 'explain', job_id: 'expl-job', output_ref_json: { outputs: [{ name: 'explain_results.xlsx' }, { name: 'explain_results.manifest.json' }, { name: 'unrelated.manifest.json' }] } }]
  }
  await open(); await ready(); await upload(['old-explanation.xlsx'])
  await wrapper.get('#localization-source-artifact').setValue('predict_batch/pred-job/predictions.csv'); await click('localization-use-artifact')
  await wrapper.get('#localization-source-artifact').setValue('explain/expl-job/explain_results.xlsx'); await click('localization-use-artifact'); await click('localization-run')
  expect(last('/localize/run').data.getAll('files[]').map(f => f.name).sort()).toEqual(['predictions.csv', 'predictions.manifest.json', 'explain_results.xlsx', 'explain_results.manifest.json'].sort())
  expect(fetchMock.mock.calls.some(([url]) => url.includes('unrelated'))).toBe(false)
  expect(fetchMock.mock.calls.every(([, o]) => 'X-API-Key' in o.headers)).toBe(true)
})
it('preserves localization and drafts on retriable source and 40001 errors', async () => {
  await open(); await ready(); await click('localization-run')
  replies['/source/file'] = [{ code: 40001, message: 'unsupported source path' }]; await chooseFile()
  expect(wrapper.text()).toContain('40001'); expect(wrapper.get('[data-testid="localization-result"]').text()).toContain('one')
  await click('localization-retry-file'); expect(wrapper.find('[data-testid="localization-code"]').exists()).toBe(true)
  replies['/localize/run'] = [{ code: 40001, message: 'missing predictions in input content' }]; await click('localization-run')
  expect(wrapper.text()).toContain('pred.csv'); expect(wrapper.get('[data-testid="localization-result"]').text()).toContain('one')
})
it('preserves drafts on artifact-library errors and retries without localization', async () => {
  replies['/jobs'] = [{ code: 50000, message: 'sources unavailable' }]
  await open(); await ready(); expect(wrapper.get('[data-testid="localization-artifact-error"]').text()).toBeTruthy()
  await click('localization-retry-artifacts'); expect(wrapper.text()).toContain('pred.csv'); expect(last('/localize/run')).toBeUndefined()
})
it('blocks writes and authenticated downloads after 401 while retaining previous output and drafts', async () => {
  await open(); await ready(); await click('localization-run')
  fetchMock.mockResolvedValue({ ok: false, status: 401, json: async () => ({ code: 40100, message: 'expired' }) })
  await click('localization-download-localization_localization_one.csv')
  expect(wrapper.text()).toContain('API Key'); expect(wrapper.get('#localization-run').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-testid="localization-save-defaults"]').attributes('disabled')).toBeDefined()
  expect(wrapper.get('[data-testid="localization-download-localization_localization_one.csv"]').attributes('disabled')).toBeDefined()
  expect(wrapper.text()).toContain('pred.csv'); expect(wrapper.find('input[type="password"]').exists()).toBe(false)
})
it('does not relabel old results as a new success until full registered evidence is read and validated', async () => {
  await open(); await ready(); await click('localization-run'); accepted = successful('two')
  fetchMock.mockImplementation(async url => url.includes('evidence_two') ? { ok: false, status: 500, json: async () => ({ message: 'temporary' }) } : blobResponse(JSON.stringify(evidence)))
  await click('localization-run')
  expect(wrapper.get('[data-testid="localization-result"]').text()).toContain('one'); expect(wrapper.get('[data-testid="localization-result"]').text()).not.toContain('two')
  await wrapper.get('#localization-repo').setValue('/dirty/repo'); fetchMock.mockResolvedValue(blobResponse(JSON.stringify(evidence)))
  await click('localization-retry-output'); expect(wrapper.get('[data-testid="localization-result"]').text()).toContain('two')
  await chooseFile(); expect(last('/source/file').params.repo_source).toBe('/original/repo')
})
it('rejects incomplete synchronous response or evidence without changing prior results', async () => {
  await open(); await ready(); await click('localization-run')
  accepted = { job_id: 'queued', status: 'queued' }; await click('localization-run')
  expect(wrapper.get('[data-testid="localization-result"]').text()).toContain('one')
  accepted = successful('invalid'); fetchMock.mockResolvedValue(blobResponse('{"rows":[]}')); await click('localization-run')
  expect(wrapper.get('[data-testid="localization-result"]').text()).toContain('one'); expect(wrapper.text()).toContain('结构')
})
it('downloads only registered outputs through real blobs, displays SHA/size and always revokes URLs', async () => {
  await open(); await ready(); await click('localization-run'); await click('localization-download-localization_localization_one.csv')
  expect(wrapper.get('[data-testid="localization-output-list"]').text()).toContain('csv-sha'); expect(wrapper.text()).toContain('100 bytes')
  expect(fetchMock.mock.calls.some(([u]) => u === '/api/localize/outputs/one/localization_localization_one.csv')).toBe(true)
  expect(URL.createObjectURL.mock.calls[0][0]).toBeInstanceOf(Blob)
  for (const { value } of URL.createObjectURL.mock.results) expect(URL.revokeObjectURL).toHaveBeenCalledWith(value)
  expect(wrapper.text()).not.toContain('patch_preview_one.diff')
})
it('discards a slow earlier commit tree response after a newer browse', async () => {
  const pending = deferred(); replies['/source/tree'] = [pending.promise]
  await open(); await wrapper.get('#localization-repo').setValue('/repo'); await wrapper.get('#localization-commit').setValue('old')
  await wrapper.get('#localization-source-browse').trigger('click'); await flushPromises()
  await wrapper.get('#localization-commit').setValue('new'); await click('localization-source-browse')
  pending.resolve({ ...tree('old'), entries: [{ type: 'blob', path: 'STALE', name: 'STALE' }] }); await flushPromises()
  expect(wrapper.text()).not.toContain('STALE'); expect(wrapper.get('[data-testid="localization-source-version"]').text()).toContain('new')
})
it('discards a slow previous file response and late unmounted output', async () => {
  const pending = deferred(); replies['/source/file'] = [pending.promise]
  await open(); await browse(); await wrapper.get('[data-testid="localization-entry-src/main.js"]').trigger('click'); await flushPromises()
  await click('localization-entry-src/main.js')
  pending.resolve({ commit_hash: 'abc', path: 'src/main.js', status: 'ok', content: 'STALE FILE', start_line: 1, end_line: 1, total_lines: 1 }); await flushPromises()
  expect(wrapper.text()).not.toContain('STALE FILE')
  await upload(); const late = deferred(); fetchMock.mockReturnValue(late.promise); await wrapper.get('#localization-run').trigger('click'); await flushPromises()
  wrapper.unmount(); wrapper = null; late.resolve(blobResponse(JSON.stringify(evidence))); await flushPromises(); expect(URL.createObjectURL).not.toHaveBeenCalled()
})
