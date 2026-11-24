<template>
  <section class="collect">
    <el-tabs
      v-model="section"
      data-testid="collect-tabs"
    >
      <el-tab-pane
        label="收集工具台"
        name="tool"
      >
        <p class="hint">
          指定 Git 仓库，交付提交、14 维特征与 SZZ 标签文件。下载无需导入；训练、预测不在本页运行。
        </p>
        <section
          class="panel"
          aria-labelledby="collect-input-title"
        >
          <h2 id="collect-input-title">
            仓库与采集范围
          </h2>
          <el-alert
            v-if="error"
            :title="error"
            type="error"
            :closable="false"
            show-icon
          />
          <form @submit.prevent="submit">
            <div class="fields">
              <label
                class="wide"
                for="collect-repo"
              >仓库路径 / URL
                <input
                  id="collect-repo"
                  v-model="draft.repo_source"
                  :disabled="busy || auth"
                  autocomplete="off"
                  placeholder="允许根目录内的本地 Git 仓库，或白名单 URL"
                >
              </label>
              <label for="collect-name">数据集名称
                <input
                  id="collect-name"
                  v-model="draft.dataset_name"
                  :disabled="busy || auth"
                  autocomplete="off"
                >
              </label>
              <label for="collect-branch">分支 / ref（留空使用 HEAD）
                <input
                  id="collect-branch"
                  v-model="draft.branch"
                  :disabled="busy || auth"
                  autocomplete="off"
                >
              </label>
              <label for="collect-start">开始时间（UTC，可选）
                <input
                  id="collect-start"
                  v-model="draft.start_time"
                  :disabled="busy || auth"
                  placeholder="2026-01-01T00:00:00Z"
                >
              </label>
              <label for="collect-end">结束时间（UTC，可选）
                <input
                  id="collect-end"
                  v-model="draft.end_time"
                  :disabled="busy || auth"
                  placeholder="2026-12-31T23:59:59Z"
                >
              </label>
              <label for="collect-dataset">已有数据集提交范围（可选）
                <select
                  id="collect-dataset"
                  v-model="draft.dataset_id"
                  :disabled="busy || auth || datasetsLoading"
                >
                  <option value="">不使用库中范围，可直接运行</option>
                  <option
                    v-for="item in datasets.items"
                    :key="item.dataset_id"
                    :value="item.dataset_id"
                  >{{ item.name }} · {{ item.dataset_id }}</option>
                </select>
              </label>
              <label for="collect-files">提交哈希清单（可选，CSV / XLSX）
                <input
                  id="collect-files"
                  type="file"
                  accept=".csv,.xlsx"
                  :disabled="busy || auth"
                  @change="selectFile"
                >
              </label>
            </div>
            <p class="hint">
              清单仅含 commit_hash 列；不选清单按仓库范围运行。时间范围只限制输出，不截断历史特征所需前序提交。仓库允许根与协议由①用户配置管理，后端进行最终安全校验。
            </p>
            <p
              v-if="file"
              class="file-note"
            >
              {{ file.name }} · {{ file.size }} bytes <el-button
                size="small"
                :disabled="busy"
                @click="file = null"
              >
                移除清单
              </el-button>
            </p>
            <details>
              <summary>采集与标注设置</summary>
              <div class="fields advanced">
                <label for="collect-mode">采集模式
                  <select
                    id="collect-mode"
                    v-model="draft.mode"
                  ><option value="incremental">增量（按提交去重）</option><option value="full">全量</option></select>
                </label>
                <label for="collect-method">SZZ 方法
                  <select
                    id="collect-method"
                    v-model="draft.szz_method"
                  ><option value="szz">szz · 行级回溯</option><option value="szz_lite">szz_lite · 文件级回溯</option></select>
                </label>
                <label for="collect-ratio">时间序训练比例
                  <input
                    id="collect-ratio"
                    v-model.number="draft.split_ratio"
                    type="number"
                    min="0.01"
                    max="0.99"
                    step="0.01"
                  >
                </label>
                <label for="collect-head">期望 HEAD（可选，40 位哈希）<input
                  id="collect-head"
                  v-model="draft.head_expect"
                ></label>
                <label for="collect-from">起始提交（可选）<input
                  id="collect-from"
                  v-model="draft.start_commit"
                ></label>
                <label for="collect-to">结束提交（可选）<input
                  id="collect-to"
                  v-model="draft.end_commit"
                ></label>
              </div>
              <label
                class="checkbox"
                for="collect-fetch"
              ><input
                id="collect-fetch"
                v-model="draft.fetch_remote"
                type="checkbox"
              >拉取远端（关闭则使用本地快照）</label>
              <p class="hint">
                使用词首修复语义判据；未打标保持空值。切分只按时间序，不支持随机划分。
              </p>
            </details>
            <div class="actions">
              <el-button
                data-testid="collect-run"
                type="primary"
                native-type="submit"
                :loading="busy"
                :disabled="busy || auth || isRunning"
              >
                运行收集
              </el-button>
              <el-button
                data-testid="collect-save-defaults"
                :loading="savingDefaults"
                :disabled="savingDefaults || auth"
                @click="saveDefaults"
              >
                保存默认分支与模式
              </el-button>
              <span class="hint">运行创建独立 collect 任务，不写入提交或数据集展示表。</span>
              <span
                role="status"
                class="hint"
              >{{ defaultsMessage }}</span>
            </div>
          </form>
        </section>
        <section
          v-if="collection.job"
          class="panel"
          data-testid="collect-job"
          aria-live="polite"
        >
          <div class="heading">
            <h2>收集任务</h2><el-tag :type="statusType">
              {{ statusLabel }}
            </el-tag>
          </div>
          <p class="mono">
            {{ collection.job.job_id }}
          </p>
          <el-progress
            :percentage="percentage"
            :status="collection.job.status === 'success' ? 'success' : undefined"
          />
          <p class="hint">
            {{ collection.job.current_item || '等待执行' }} · {{ collection.job.done ?? 0 }} / {{ collection.job.total ?? 0 }} · 重试 {{ collection.job.retry_count ?? 0 }} 次
          </p>
          <el-alert
            v-if="collection.job.error_log"
            :title="collection.job.error_log"
            type="error"
            :closable="false"
          />
          <div class="actions">
            <el-button
              :disabled="jobLoading || auth"
              @click="refreshJob"
            >
              刷新状态
            </el-button>
            <el-button
              v-if="collection.job.status === 'failed'"
              data-testid="collect-retry"
              :disabled="jobLoading || auth"
              @click="retry"
            >
              重试原任务
            </el-button>
            <el-button
              v-if="isRunning"
              data-testid="collect-cancel"
              :disabled="jobLoading || auth"
              @click="cancel"
            >
              取消任务
            </el-button>
          </div>
        </section>
        <section
          v-if="result && collection.job?.status === 'success'"
          class="panel"
          aria-labelledby="collect-output-title"
        >
          <h2 id="collect-output-title">
            本次收集输出
          </h2>
          <dl class="stats">
            <div><dt>样本</dt><dd>{{ result.summary?.rows }}</dd></div>
            <div><dt>正样本</dt><dd>{{ result.summary?.positive_rows }}</dd></div>
            <div><dt>负样本</dt><dd>{{ result.summary?.negative_rows }}</dd></div>
            <div><dt>未打标</dt><dd>{{ result.summary?.unlabeled_rows }}</dd></div>
          </dl>
          <p class="mono">
            HEAD {{ result.summary?.head_hash }}
          </p>
          <p class="hint">
            commits 契约：元信息 + Kamei 14 维固定列序 + 标签 + 时间序划分；fix 不做 log。以下仅预览前 20 行，完整文件由下载按钮交付。
          </p>
          <el-alert
            v-if="previewError"
            :title="previewError"
            type="error"
            :closable="false"
          />
          <div
            v-if="collection.preview"
            class="table-scroll"
            data-testid="collect-preview"
          >
            <table>
              <thead>
                <tr>
                  <th
                    v-for="column in collection.preview.columns"
                    :key="column"
                  >
                    {{ column }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in collection.preview.preview"
                  :key="row.commit_hash"
                >
                  <td
                    v-for="column in collection.preview.columns"
                    :key="column"
                  >
                    {{ cell(row[column], column) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="actions">
            <el-button
              data-testid="collect-download-csv"
              :disabled="downloading || auth || !artifact('csv')"
              @click="download(artifact('csv'))"
            >
              下载 CSV
            </el-button>
            <el-button
              :disabled="downloading || auth || !artifact('xlsx')"
              @click="download(artifact('xlsx'))"
            >
              下载 XLSX
            </el-button>
            <el-button
              :disabled="downloading || auth"
              @click="download(result.manifest_name)"
            >
              下载 manifest
            </el-button>
          </div>
          <ul class="output-list">
            <li
              v-for="item in result.outputs"
              :key="item.name"
            >
              <span>{{ item.name }} · {{ item.size_bytes }} bytes</span><code>{{ item.sha256 }}</code>
            </li>
          </ul>
          <div class="import-block">
            <h3>可选导入展示库</h3>
            <p class="hint">
              仅在点击后提交 CSV 与同批 manifest。风险列表、趋势仍需预测结果，不会因收集完成而出现概率。
            </p>
            <div class="fields">
              <label for="collect-import-name">登记数据集名称<input
                id="collect-import-name"
                v-model="importDraft.name"
              ></label>
              <label for="collect-import-source">登记来源仓库<input
                id="collect-import-source"
                v-model="importDraft.repo_source"
              ></label>
            </div>
            <el-button
              data-testid="collect-import"
              :loading="importing"
              :disabled="importing || auth"
              @click="importResult"
            >
              导入提交与数据集
            </el-button>
            <p
              role="status"
              class="hint"
            >
              {{ importMessage }}
            </p>
          </div>
        </section>
      </el-tab-pane>
      <el-tab-pane
        label="已收集数据集"
        name="datasets"
      >
        <p class="hint">
          这里只展示已显式导入的资产；暂无数据不影响收集工具。<router-link to="/storage">
            去①数据管理导入
          </router-link>
        </p>
        <el-alert
          v-if="datasetsError"
          :title="datasetsError"
          type="error"
          :closable="false"
        />
        <el-button
          :loading="datasetsLoading"
          @click="loadDatasets"
        >
          刷新已导入数据集
        </el-button>
        <el-table
          :data="datasets.items"
          border
          class="dataset-table"
        >
          <el-table-column
            prop="name"
            label="数据集名称"
            min-width="170"
          />
          <el-table-column
            prop="repo_source"
            label="来源仓库"
            min-width="230"
            show-overflow-tooltip
          />
          <el-table-column
            prop="branch"
            label="分支"
            min-width="100"
          />
          <el-table-column
            prop="head_hash"
            label="HEAD"
            min-width="180"
            show-overflow-tooltip
          />
          <el-table-column
            prop="sample_count"
            label="样本"
            width="80"
          />
          <el-table-column
            prop="pos_count"
            label="正样本"
            width="80"
          />
          <el-table-column
            prop="neg_count"
            label="负样本"
            width="80"
          />
          <el-table-column
            label="未打标"
            width="80"
          >
            <template #default="{ row }">
              {{ row.sample_count - row.pos_count - row.neg_count }}
            </template>
          </el-table-column>
          <el-table-column
            prop="status"
            label="状态"
            width="100"
          />
          <el-table-column
            prop="created_at"
            label="创建时间"
            min-width="180"
          />
          <el-table-column
            label="提交样本"
            width="100"
          >
            <template #default="{ row }">
              <el-button
                size="small"
                @click="openMembers(row)"
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="datasetPage"
          :total="datasets.total"
          :page-size="20"
          layout="prev, pager, next, total"
          @current-change="loadDatasets"
        />
      </el-tab-pane>
    </el-tabs>
    <el-dialog
      v-model="membersOpen"
      :title="membersTitle"
      width="90%"
    >
      <el-alert
        v-if="membersError"
        :title="membersError"
        type="error"
        :closable="false"
      />
      <el-table
        :data="members.items"
        border
      >
        <el-table-column
          prop="commit_hash"
          label="提交"
          min-width="180"
          show-overflow-tooltip
        />
        <el-table-column
          prop="message"
          label="提交信息"
          min-width="200"
        />
        <el-table-column
          prop="committed_at"
          label="UTC 时间"
          min-width="180"
        />
        <el-table-column
          label="标签"
          width="100"
        >
          <template #default="{ row }">
            {{ cell(row.is_bug_inducing, 'is_bug_inducing') }}
          </template>
        </el-table-column>
        <el-table-column
          label="14 维特征"
          min-width="280"
        >
          <template #default="{ row }">
            <code>{{ JSON.stringify(Object.fromEntries(FEATURE_FIELDS.map(field => [field, row[field]]))) }}</code>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="membersPage"
        :page-size="20"
        :total="members.total"
        layout="prev, pager, next, total"
        @current-change="loadMembers"
      />
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { cancelJob, fetchCollectOutput, getCollectPreview, getDatasetCommits, getDatasets, getJob, getJobs, importStorageFiles, putConfigKey, retryJob, runCollect } from '../api'
import { collection } from '../utils/collect'
import { FEATURE_FIELDS } from '../utils/features'
import { configuration, loadConfiguration } from '../utils/thresholds'

defineOptions({ name: 'CollectTool' })

const section = ref('tool')
const draft = reactive({ repo_source: '', dataset_name: '', branch: '', start_time: '', end_time: '', start_commit: '', end_commit: '', head_expect: '', dataset_id: '', mode: 'incremental', fetch_remote: true, szz_method: 'szz', split_ratio: 0.7 })
const importDraft = reactive({ name: '', repo_source: '' })
const file = ref(null), busy = ref(false), error = ref(''), auth = ref(false), jobLoading = ref(false)
const savingDefaults = ref(false), defaultsMessage = ref('')
const previewError = ref(''), downloading = ref(false), importing = ref(false), importMessage = ref('')
const datasets = reactive({ items: [], total: 0 }), datasetsLoading = ref(false), datasetsError = ref(''), datasetPage = ref(1)
const members = reactive({ items: [], total: 0 }), membersOpen = ref(false), membersTitle = ref(''), membersError = ref(''), membersPage = ref(1)
let memberId = '', memberEpoch = 0, timer, mounted = true
const result = computed(() => collection.job?.output_ref_json)
const isRunning = computed(() => ['queued', 'running'].includes(collection.job?.status))
const statusLabel = computed(() => ({ queued: '排队中', running: '运行中', success: '成功', failed: '失败', cancelled: '已取消' })[collection.job?.status] || '')
const statusType = computed(() => ({ success: 'success', failed: 'danger', cancelled: 'info' })[collection.job?.status] || 'primary')
const percentage = computed(() => collection.job?.total ? Math.min(100, Math.floor(collection.job.done / collection.job.total * 100)) : 0)

function message(err) {
  if (err.code === 40100) { auth.value = true; return '鉴权失败，请检查部署环境中的 API Key' }
  return err.code === 50000 ? '服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
function cell(value, column) { return value == null || value === '' ? column === 'is_bug_inducing' ? '未打标' : '' : value }
function artifact(format) { return result.value?.outputs?.find(item => item.name.endsWith('.' + format))?.name }
function selectFile(event) { file.value = event.target.files?.[0] || null; event.target.value = '' }

function configItem(key) { return configuration.items.find(item => item.config_key === key) }
function normalizePath(path) {
  const parts = []
  for (const part of path.split('/')) {
    if (part === '..') parts.pop()
    else if (part && part !== '.') parts.push(part)
  }
  return '/' + parts.join('/')
}
function sourceError(source) {
  if (source.includes('://')) {
    let url
    try { url = new URL(source) } catch { return '仓库 URL 格式非法' }
    if (!url.hostname || url.username || url.password || url.search || url.hash) return '仓库 URL 不允许凭证、查询参数或片段'
    const policy = configItem('collect.protocol_whitelist')
    if (policy && !policy.value.includes(url.protocol.slice(0, -1))) return '仓库协议不在白名单内'
  } else {
    if (!source.startsWith('/')) return '请输入绝对本地路径或仓库 URL'
    const policy = configItem('collect.allow_roots')
    const path = normalizePath(source)
    if (policy && !policy.value.some(root => {
      root = normalizePath(root)
      return root === '/' || path === root || path.startsWith(root + '/')
    })) return '仓库路径不在允许根目录内'
  }
  return ''
}
async function saveDefaults() {
  if (savingDefaults.value || auth.value) return
  savingDefaults.value = true; defaultsMessage.value = ''; error.value = ''
  try {
    await putConfigKey('page_prefs', { ...configItem('page_prefs')?.value,
      collect_branch: draft.branch, collect_mode: draft.mode })
    await loadConfiguration()
    defaultsMessage.value = '页面默认值已保存（全局），已创建任务的参数不变'
  } catch (err) { error.value = message(err) }
  finally { savingDefaults.value = false }
}

async function submit() {
  if (busy.value || auth.value || isRunning.value) return
  error.value = ''
  if ((!draft.repo_source.trim() && !draft.dataset_id) || !draft.dataset_name.trim()) {
    error.value = '请填写仓库路径 / URL（或选择数据集范围）与数据集名称'; return
  }
  const config = Object.fromEntries(Object.entries(draft).filter(([, value]) => value !== ''))
  config.dataset_name = draft.dataset_name.trim()
  if (config.repo_source) {
    config.repo_source = config.repo_source.trim()
    const validation = sourceError(config.repo_source)
    if (validation) { error.value = validation; return }
  }
  busy.value = true
  try {
    const accepted = await runCollect(config, file.value ? [file.value] : [])
    if (!accepted?.job_id || !['queued', 'running', 'success'].includes(accepted.status)) throw new Error('收集响应不完整')
    collection.request = { ...config }
    collection.preview = null
    collection.job = accepted
    importDraft.name = config.dataset_name
    importDraft.repo_source = config.repo_source || ''
    importMessage.value = ''
    await refreshJob()
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}

async function refreshJob() {
  if (!collection.job?.job_id || jobLoading.value || auth.value) return
  clearTimeout(timer)
  const id = collection.job.job_id
  jobLoading.value = true
  try {
    const job = await getJob(id)
    if (collection.job?.job_id !== id) return
    if (job.job_id !== id || !['queued', 'running', 'success', 'failed', 'cancelled'].includes(job.status)) throw new Error('任务响应不完整')
    collection.job = job
    if (job.status === 'success' && !collection.preview) {
      try { collection.preview = await getCollectPreview(id); previewError.value = '' }
      catch (err) { previewError.value = message(err) }
    }
    if (mounted && ['queued', 'running'].includes(job.status)) timer = setTimeout(refreshJob, 1500)
  } catch (err) { error.value = message(err) }
  finally { jobLoading.value = false }
}
async function retry() {
  try {
    const data = await retryJob(collection.job.job_id)
    collection.job = { ...collection.job, ...data }
    collection.preview = null
    await refreshJob()
  } catch (err) { error.value = message(err) }
}
async function cancel() {
  try {
    const data = await cancelJob(collection.job.job_id)
    collection.job = { ...collection.job, ...data }
    clearTimeout(timer)
  } catch (err) { error.value = message(err) }
}
async function download(name) {
  downloading.value = true
  try {
    const blob = await fetchCollectOutput(collection.job.job_id, name)
    const url = URL.createObjectURL(blob)
    try { const link = document.createElement('a'); link.href = url; link.download = name; link.click() }
    finally { URL.revokeObjectURL(url) }
  } catch (err) { error.value = message(err) }
  finally { downloading.value = false }
}
async function importResult() {
  importMessage.value = ''
  if (!importDraft.name.trim() || !importDraft.repo_source.trim()) { importMessage.value = '请填写登记数据集名称与来源仓库'; return }
  importing.value = true
  try {
    const id = collection.job.job_id, name = artifact('csv'), manifest = result.value.manifest_name
    const blobs = await Promise.all([fetchCollectOutput(id, name), fetchCollectOutput(id, manifest)])
    const response = await importStorageFiles([new File([blobs[0]], name), new File([blobs[1]], manifest)], {
      create_dataset: { name: importDraft.name.trim(), repo_source: importDraft.repo_source.trim(), head_hash: result.value.summary.head_hash }
    })
    if (!response?.items?.length || !response.summary) throw new Error('导入响应不完整')
    if (response.summary.rejected || response.items.some(item => item.status === 'rejected')) {
      importMessage.value = '存在拒绝项：' + response.items.flatMap(item => item.errors || []).join('；'); return
    }
    importMessage.value = '提交与数据集已入库，可供详情页与后续模块选用'
    await loadDatasets()
  } catch (err) { importMessage.value = message(err) }
  finally { importing.value = false }
}
async function loadDatasets() {
  datasetsLoading.value = true; datasetsError.value = ''
  try {
    const data = await getDatasets({ page: datasetPage.value, size: 20 })
    if (!Array.isArray(data?.items) || typeof data.total !== 'number') throw new Error('数据集响应不完整')
    Object.assign(datasets, data)
  } catch (err) { datasetsError.value = message(err) }
  finally { datasetsLoading.value = false }
}
async function openMembers(row) {
  memberId = row.dataset_id; membersTitle.value = row.name; membersPage.value = 1
  membersOpen.value = true; await loadMembers()
}
async function loadMembers() {
  const epoch = ++memberEpoch
  membersError.value = ''; members.items = []
  try {
    const data = await getDatasetCommits(memberId, { page: membersPage.value, size: 20 })
    if (epoch === memberEpoch) Object.assign(members, data)
  } catch (err) { if (epoch === memberEpoch) membersError.value = message(err) }
}
onMounted(async () => {
  const prefs = configItem('page_prefs')?.value || {}
  draft.branch = prefs.collect_branch ?? ''
  draft.mode = prefs.collect_mode ?? 'incremental'
  loadDatasets()
  if (!collection.job) {
    try { const data = await getJobs({ kind: 'collect', page: 1, size: 1 }); collection.job = data.items?.[0] || null }
    catch (err) { error.value = message(err) }
  }
  if (collection.request) { importDraft.name = collection.request.dataset_name; importDraft.repo_source = collection.request.repo_source || '' }
  await refreshJob()
})
onUnmounted(() => { mounted = false; clearTimeout(timer); memberEpoch++ })
</script>

<style scoped>
.collect { min-width: 0; }
.panel { border: 1px solid var(--el-border-color-light); border-radius: var(--el-border-radius-base); padding: 18px; margin: 18px 0; }
h2 { margin: 0 0 16px; font-size: 16px; }
h3 { font-size: 14px; margin: 0 0 12px; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.65; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 16px 0; }
.fields label { display: flex; flex-direction: column; gap: 8px; font-size: 14px; color: var(--el-text-color-regular); min-width: 0; }
.wide { grid-column: 1 / -1; }
input:not([type="checkbox"]), select { box-sizing: border-box; width: 100%; min-width: 0; border: 1px solid var(--el-border-color); border-radius: var(--el-border-radius-base); padding: 8px 10px; background: var(--el-fill-color-blank); color: var(--el-text-color-primary); font: inherit; }
input:focus-visible, select:focus-visible, summary:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 2px; }
input:disabled { background: var(--el-fill-color-light); }
.checkbox { display: flex; align-items: center; gap: 8px; font-size: 14px; }
summary { cursor: pointer; font-size: 14px; padding: 10px 0; }
.actions, .heading { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 16px; }
.heading h2 { margin: 0; }
.mono, code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; overflow-wrap: anywhere; }
.stats { display: flex; flex-wrap: wrap; gap: 28px; margin: 16px 0; }
.stats dt { color: var(--el-text-color-secondary); font-size: 13px; }
.stats dd { margin: 6px 0 0; font-variant-numeric: tabular-nums; font-size: 20px; }
.table-scroll { overflow-x: auto; max-width: 100%; }
table { border-collapse: collapse; font-size: 12px; white-space: nowrap; }
th, td { border: 1px solid var(--el-border-color-light); padding: 10px; text-align: left; max-width: 280px; overflow: hidden; text-overflow: ellipsis; }
th { background: var(--el-fill-color-light); }
.output-list { padding: 0; list-style: none; font-size: 12px; }
.output-list li { display: grid; gap: 5px; border-bottom: 1px solid var(--el-border-color-lighter); padding: 10px 0; overflow-wrap: anywhere; }
.import-block { border-top: 1px solid var(--el-border-color-light); margin-top: 22px; padding-top: 18px; }
.dataset-table { margin: 16px 0; max-width: 100%; }
.file-note { font-size: 13px; overflow-wrap: anywhere; }
@media (max-width: 640px) { .fields { grid-template-columns: minmax(0, 1fr); } .panel { padding: 14px; } .stats { gap: 18px; } .actions > .el-button { margin-left: 0; } }
</style>
