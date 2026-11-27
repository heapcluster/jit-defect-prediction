<template>
  <section class="storage">
    <ToolWorkspace
      base="/storage"
      :items="tabs"
      :model-value="active"
    >
      <!-- 数据链路：按 chain_id 汇总任务与产物，支持整链删除 -->
      <template #lineage>
        <el-alert
          v-if="lineageState.error"
          :title="lineageState.error"
          type="error"
          :closable="false"
          class="notice"
        />
        <FilterBar>
          <el-button
            :loading="lineageState.loading"
            :disabled="lineageState.loading"
            @click="loadLineage"
          >
            刷新链路
          </el-button>
          <span class="status-line">整链删除会一并移除链内任务、产物、模型与数据集，被链路外引用时拒绝删除。</span>
        </FilterBar>
        <el-skeleton
          v-if="lineageState.loading && !lineage.items.length"
          :rows="5"
          animated
        />
        <EmptyState
          v-else-if="!lineage.items.length"
          :title="lineageState.error ? '读取失败' : '暂无数据链路'"
          :description="lineageState.error ? '' : '收集、清洗、训练等任务会按链路聚合显示。'"
        />
        <el-table
          v-else
          :data="lineage.items"
          row-key="chain_id"
          border
          size="small"
          data-testid="artifact-lineage"
        >
          <el-table-column type="expand">
            <template #default="{ row }">
              <el-table
                :data="row.nodes"
                border
                size="small"
              >
                <el-table-column
                  label="类型"
                  width="110"
                >
                  <template #default="{ row: node }">
                    {{ TYPE_LABELS[node.kind] || node.kind }}
                  </template>
                </el-table-column>
                <el-table-column
                  prop="job_id"
                  label="任务编号"
                  min-width="180"
                  show-overflow-tooltip
                />
                <el-table-column
                  label="状态"
                  width="90"
                >
                  <template #default="{ row: node }">
                    {{ STATUS_LABELS[node.status] || node.status }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="产物"
                  min-width="240"
                  show-overflow-tooltip
                >
                  <template #default="{ row: node }">
                    {{ (node.artifacts || []).map(item => item.name).join('，') || '—' }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="模型 / 数据集"
                  min-width="180"
                  show-overflow-tooltip
                >
                  <template #default="{ row: node }">
                    {{ [...(node.model_names || []), node.dataset_id].filter(Boolean).join('，') || '—' }}
                  </template>
                </el-table-column>
              </el-table>
            </template>
          </el-table-column>
          <el-table-column
            prop="title"
            label="链路"
            min-width="220"
            show-overflow-tooltip
          />
          <el-table-column
            label="节点"
            width="80"
          >
            <template #default="{ row }">
              {{ row.node_count }}
            </template>
          </el-table-column>
          <el-table-column
            label="类型分布"
            min-width="220"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              {{ kindSummary(row.kinds) }}
            </template>
          </el-table-column>
          <el-table-column
            label="创建时间"
            min-width="150"
          >
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column
            label="操作"
            width="110"
          >
            <template #default="{ row }">
              <el-button
                link
                type="danger"
                :loading="deletingChain === row.chain_id"
                :disabled="lineageState.auth"
                @click="removeChain(row)"
              >
                整链删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>

      <!-- 产物库：全部历史产物的唯一入口 -->
      <template #library>
        <el-alert
          v-if="libraryState.error"
          :title="libraryState.error"
          type="error"
          :closable="false"
          class="notice"
        >
          <el-button
            v-if="!libraryState.auth"
            :disabled="libraryState.loading"
            @click="loadLibrary"
          >
            重试读取产物
          </el-button>
        </el-alert>

        <StatGrid :items="statItems" />

        <FilterBar>
          <el-select
            v-model="filters.type"
            aria-label="产物类型"
            class="filter-control"
            @change="resetPage"
          >
            <el-option
              v-for="option in typeOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-select
            v-model="filters.status"
            aria-label="产物状态"
            class="filter-control"
            @change="resetPage"
          >
            <el-option
              label="全部状态"
              value="all"
            />
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-input
            v-model="filters.keyword"
            data-testid="library-keyword"
            aria-label="搜索产物名称或任务编号"
            placeholder="搜索名称 / 任务编号"
            clearable
            class="filter-control filter-control--wide"
            @input="resetPage"
          />
          <template #actions>
            <el-button
              :loading="libraryState.loading"
              :disabled="libraryState.loading"
              @click="loadLibrary"
            >
              刷新
            </el-button>
          </template>
        </FilterBar>

        <el-skeleton
          v-if="libraryState.loading && !rows.length"
          :rows="5"
          animated
        />
        <EmptyState
          v-else-if="!filteredRows.length"
          :title="libraryState.error ? '读取失败' : '暂无匹配产物'"
          :description="libraryState.error ? '' : '收集、清洗、训练等任务的结果会显示在这里。'"
        />
        <template v-else>
          <div class="table-scroll">
            <el-table
              :data="pagedRows"
              border
              size="small"
              data-testid="artifact-library"
            >
              <el-table-column
                prop="name"
                label="名称"
                min-width="168"
                show-overflow-tooltip
              />
              <el-table-column
                prop="type"
                label="类型"
                width="96"
              />
              <el-table-column
                prop="source"
                label="来源任务"
                min-width="150"
                show-overflow-tooltip
              />
              <el-table-column
                label="生成时间"
                min-width="136"
              >
                <template #default="{ row }">
                  {{ formatDateTime(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column
                label="产物文件"
                width="86"
              >
                <template #default="{ row }">
                  {{ row?.files?.length ? `${row.files.length} 个` : '—' }}
                </template>
              </el-table-column>
              <el-table-column
                prop="statusLabel"
                label="状态"
                width="82"
              />
              <el-table-column
                label="操作"
                min-width="164"
              >
                <template #default="{ row }">
                  <el-button
                    link
                    type="primary"
                    data-testid="view-artifact"
                    @click="openViewer(row)"
                  >
                    查看
                  </el-button>
                  <el-button
                    link
                    type="primary"
                    :disabled="libraryState.auth || (row?.kind !== 'dataset' && !row?.files?.length)"
                    @click="downloadPrimary(row)"
                  >
                    下载
                  </el-button>
                  <el-button
                    v-if="row.kind === 'dataset'"
                    link
                    type="danger"
                    data-testid="delete-dataset"
                    :loading="deletingKey === row.key"
                    :disabled="libraryState.auth"
                    @click="removeDataset(row)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <el-pagination
            class="pagination"
            background
            layout="total, prev, pager, next"
            :current-page="page"
            :page-size="pageSize"
            :total="filteredRows.length"
            hide-on-single-page
            @current-change="page = $event"
          />
        </template>
      </template>
    </ToolWorkspace>

    <!-- 产物查看抽屉 -->
    <el-drawer
      v-model="viewer.open"
      :title="viewer.row ? viewer.row.name : '产物详情'"
      size="min(880px, calc(100vw - 32px))"
      append-to-body
    >
      <template v-if="viewer.row">
        <InfoGrid :items="viewerInfo" />

        <section
          v-if="viewer.row.kind !== 'dataset'"
          aria-label="产物文件"
        >
          <div class="section-heading">
            <h2>产物文件</h2>
          </div>
          <ul
            v-if="viewer.row.files.length"
            class="file-list"
          >
            <li
              v-for="file in viewer.row.files"
              :key="file.name"
            >
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ formatSize(file.size_bytes) }}</span>
              <el-button
                link
                type="primary"
                data-testid="download-artifact-file"
                :disabled="libraryState.auth || downloadingKey === file.name"
                @click="downloadFile(viewer.row, file)"
              >
                下载
              </el-button>
            </li>
          </ul>
          <p
            v-else
            class="ui-note"
          >
            该任务没有登记可下载的产物文件。
          </p>
        </section>

        <section
          v-else
          aria-label="数据集成员"
        >
          <div class="section-heading">
            <h2>数据集成员</h2>
          </div>
          <el-alert
            v-if="viewer.membersError"
            :title="viewer.membersError"
            type="error"
            :closable="false"
            class="notice"
          />
          <p
            v-if="viewer.membersLoading"
            role="status"
            class="ui-note"
          >
            正在读取成员…
          </p>
          <DataTable
            v-else
            :columns="memberColumns"
            :rows="viewer.members"
            empty="当前数据集暂无成员。"
          />
          <el-pagination
            v-if="viewer.membersTotal"
            class="pagination"
            background
            layout="prev, pager, next"
            :current-page="viewer.membersPage"
            :page-size="20"
            :total="viewer.membersTotal"
            hide-on-single-page
            @current-change="loadMembers"
          />
        </section>
      </template>
    </el-drawer>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import DataTable from '../components/DataTable.vue'
import EmptyState from '../components/EmptyState.vue'
import FilterBar from '../components/FilterBar.vue'
import InfoGrid from '../components/InfoGrid.vue'
import StatGrid from '../components/StatGrid.vue'
import ToolWorkspace from '../components/ToolWorkspace.vue'
import {
  deleteDataset,
  deleteStorageChain,
  exportStorageTable,
  fetchStorageOutput,
  getDatasetCommits,
  getDatasets,
  getJobs,
  getStorageLineage
} from '../api'
import { downloadArtifact } from '../utils/artifacts'
import { saveBlob } from '../utils/download'
import { formatDateTime } from '../utils/datetime'

defineOptions({ name: 'StorageWorkspace' })

const tabs = [
  { name: 'library', label: '产物库', title: '产物库' },
  { name: 'lineage', label: '数据链路', title: '数据链路' }
]
const route = useRoute()
const active = computed(() => (route.query.section === 'lineage' ? 'lineage' : 'library'))

const state = () => reactive({ loading: false, error: '', auth: false })
const libraryState = state()
const lineageState = state()
const lineage = reactive({ items: [], total: 0 })
const deletingChain = ref('')

const TYPE_LABELS = {
  dataset: '数据集',
  collect: '收集结果',
  clean: '清洗结果',
  train: '训练结果',
  predict_batch: '预测结果',
  evaluate: '评估结果',
  explain: '解释结果'
}
const JOB_KINDS = ['collect', 'clean', 'train', 'predict_batch', 'evaluate', 'explain']
const STATUS_LABELS = {
  queued: '排队中',
  running: '运行中',
  success: '成功',
  failed: '失败',
  cancelled: '已取消',
  ready: '就绪'
}
const TYPE_OPTIONS = [
  { value: 'all', label: '全部产物' },
  { value: 'dataset', label: '数据集' },
  ...JOB_KINDS.map(kind => ({ value: kind, label: TYPE_LABELS[kind] }))
]
const STATUS_OPTIONS = Object.entries(STATUS_LABELS).map(([value, label]) => ({ value, label }))

const jobs = ref([])
const datasetItems = ref([])
const counts = reactive({ dataset: null, collect: null, clean: null, train: null, predict_batch: null, evaluate: null, explain: null })
const filters = reactive({ type: 'all', status: 'all', keyword: '' })
const page = ref(1)
const pageSize = 20
const deletingKey = ref('')
const downloadingKey = ref('')

const statItems = computed(() => [
  { key: 'dataset', label: '数据集', value: counts.dataset },
  ...JOB_KINDS.map(kind => ({ key: kind, label: TYPE_LABELS[kind], value: counts[kind] }))
])

function showError(target, error, fallback) {
  if (error.code === 40100) {
    target.auth = true
    target.error = '登录已失效，请重新登录。'
  } else if (error.code === 50000 || error.response?.status >= 500) {
    target.error = '服务异常，请稍后重试'
  } else if (error.code === 40400) {
    target.error = '产物不存在，请刷新列表'
  } else {
    target.error = error.code === 40001 ? '填写有误，请检查输入' : error.message || fallback
  }
}

function jobName(job) {
  const outputName = job.params_json?.config?.output_name
  if (typeof outputName === 'string' && outputName.trim()) return outputName
  const summary = job.output_ref_json?.summary || {}
  switch (job.kind) {
    case 'collect':
      return summary.total_rows != null ? `收集结果（${summary.total_rows} 条）` : '收集结果'
    case 'clean':
      return summary.output_rows != null ? `清洗结果（${summary.output_rows} 条）` : '清洗结果'
    case 'train': {
      const models = job.output_ref_json?.models || []
      return models.length ? `训练结果（${models.length} 个模型）` : '训练结果'
    }
    case 'predict_batch':
      return summary.input_rows != null ? `预测结果（${summary.input_rows} 条）` : '预测结果'
    case 'evaluate':
      return summary.rows != null ? `评估结果（${summary.rows} 条）` : '评估结果'
    case 'explain':
      return summary.input_rows != null ? `解释结果（${summary.input_rows} 条）` : '解释结果'
    default:
      return '处理结果'
  }
}

function normalizeJobRow(job) {
  const outputs = job.output_ref_json?.outputs || job.outputs || []
  return {
    key: `job:${job.job_id}`,
    kind: job.kind,
    type: TYPE_LABELS[job.kind] || job.kind,
    name: jobName(job),
    source: TYPE_LABELS[job.kind] || job.kind,
    created_at: job.created_at,
    status: job.status,
    statusLabel: STATUS_LABELS[job.status] || job.status || '',
    job_id: job.job_id,
    files: outputs
      .filter(item => typeof item?.name === 'string' && item.name)
      .map(item => ({ name: item.name, size_bytes: item.size_bytes }))
  }
}

function normalizeDatasetRow(dataset) {
  return {
    key: `dataset:${dataset.dataset_id}`,
    kind: 'dataset',
    type: '数据集',
    name: dataset.name,
    source: dataset.source_type === 'git_repo'
      ? `Git · ${dataset.branch || '默认分支'}`
      : (dataset.source_url || dataset.repo_source || '数据集库'),
    created_at: dataset.created_at,
    status: dataset.status,
    statusLabel: STATUS_LABELS[dataset.status] || dataset.status || '可用',
    files: [],
    dataset
  }
}

const rows = computed(() => [
  ...datasetItems.value.map(normalizeDatasetRow),
  ...jobs.value.map(normalizeJobRow)
].sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || ''))))

const filteredRows = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase()
  return rows.value.filter(row => {
    if (filters.type !== 'all' && row.kind !== filters.type) return false
    if (filters.status !== 'all' && row.status !== filters.status) return false
    if (!keyword) return true
    return `${row.name} ${row.job_id || row.dataset?.dataset_id || ''}`.toLowerCase().includes(keyword)
  })
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize
  return filteredRows.value.slice(start, start + pageSize)
})

const typeOptions = TYPE_OPTIONS
const statusOptions = STATUS_OPTIONS

function resetPage() {
  page.value = 1
}

async function loadCounts() {
  const requests = JOB_KINDS.map(kind => getJobs({ kind, size: 1 })
    .then(data => [kind, typeof data?.total === 'number' ? data.total : null])
    .catch(() => [kind, null]))
  const datasetRequest = getDatasets({ page: 1, size: 1 })
    .then(data => (typeof data?.total === 'number' ? data.total : null))
    .catch(() => null)
  const results = await Promise.all([Promise.all(requests), datasetRequest])
  for (const [kind, total] of results[0]) counts[kind] = total
  counts.dataset = results[1]
}

async function loadLibrary() {
  if (libraryState.loading) return
  libraryState.loading = true
  libraryState.error = ''
  try {
    const [jobPage, datasetPage] = await Promise.all([
      getJobs({ page: 1, size: 100 }),
      getDatasets({ page: 1, size: 100 })
    ])
    if (!Array.isArray(jobPage?.items) || !Array.isArray(datasetPage?.items)) throw new Error('产物列表响应不完整，请重试')
    jobs.value = jobPage.items.filter(item => JOB_KINDS.includes(item.kind))
    datasetItems.value = datasetPage.items
    resetPage()
    loadCounts()
  } catch (error) {
    showError(libraryState, error, '产物列表读取失败')
  } finally {
    libraryState.loading = false
  }
}

function kindSummary(kinds) {
  return Object.entries(kinds || {})
    .map(([kind, count]) => `${TYPE_LABELS[kind] || kind} ${count}`)
    .join(' / ') || '—'
}

async function loadLineage() {
  if (lineageState.loading) return
  lineageState.loading = true
  lineageState.error = ''
  try {
    const data = await getStorageLineage({ page: 1, size: 100 })
    if (!Array.isArray(data?.items)) throw new Error('链路响应不完整，请重试')
    lineage.items = data.items
    lineage.total = data.total || data.items.length
  } catch (error) {
    showError(lineageState, error, '数据链路读取失败')
  } finally {
    lineageState.loading = false
  }
}

async function removeChain(row) {
  try {
    await ElMessageBox.confirm(
      `确认整链删除「${row.title}」？链内 ${row.node_count} 个任务及其产物、模型与数据集会一并移除。`,
      '整链删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  deletingChain.value = row.chain_id
  try {
    await deleteStorageChain(row.chain_id)
    ElMessage.success('已删除整条链路')
    await Promise.all([loadLineage(), loadLibrary()])
  } catch (error) {
    ElMessage.error(error.message || '整链删除失败，请检查共享引用后重试')
  } finally {
    deletingChain.value = ''
  }
}

const viewer = reactive({
  open: false,
  row: null,
  members: [],
  membersPage: 1,
  membersTotal: 0,
  membersLoading: false,
  membersError: ''
})
const memberColumns = [
  { key: 'commit_hash', label: '提交编号', mono: true },
  { key: 'committed_at', label: '提交时间' },
  { key: 'message', label: '说明' },
  { key: 'label', label: '标注结果' }
]
const viewerInfo = computed(() => {
  const row = viewer.row
  if (!row) return []
  const rows = [
    { label: '类型', value: row.type },
    { label: '生成时间', value: formatDateTime(row.created_at) },
    { label: '状态', value: row.statusLabel }
  ]
  if (row.kind === 'dataset') {
    const data = row.dataset || {}
    rows.push(
      { label: '来源仓库', value: data.repo_source || '—', mono: true },
      { label: '分支', value: data.branch || '—' },
      { label: 'HEAD', value: data.head_hash || '—', mono: true },
      { label: '样本数', value: data.sample_count },
      {
        label: '正 / 负 / 未标注',
        value: `${data.pos_count} / ${data.neg_count} / ${Math.max(data.sample_count - data.pos_count - data.neg_count, 0)}`
      }
    )
  } else {
    rows.push(
      { label: '来源任务', value: row.source },
      { label: '任务编号', value: row.job_id, mono: true }
    )
  }
  return rows
})

function openViewer(row) {
  viewer.open = true
  viewer.row = row
  viewer.members = []
  viewer.membersPage = 1
  viewer.membersTotal = 0
  viewer.membersError = ''
  if (row.kind === 'dataset') loadMembers(1)
}

async function loadMembers(nextPage = 1) {
  const datasetId = viewer.row?.dataset?.dataset_id
  if (!datasetId || viewer.membersLoading) return
  viewer.membersLoading = true
  viewer.membersError = ''
  try {
    const data = await getDatasetCommits(datasetId, { page: nextPage, size: 20, with_features: 1 })
    if (!Array.isArray(data?.items) || typeof data.total !== 'number') throw new Error('成员响应不完整，请重试')
    viewer.members = data.items.map(item => ({
      ...item,
      label: item.label ?? item.is_bug_inducing ?? '未标注'
    }))
    viewer.membersPage = data.page || nextPage
    viewer.membersTotal = data.total
  } catch (error) {
    showError(viewer, error, '成员读取失败')
  } finally {
    viewer.membersLoading = false
  }
}

function formatSize(bytes) {
  if (typeof bytes !== 'number' || bytes < 0) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function downloadFile(row, file) {
  if (libraryState.auth || downloadingKey.value) return
  downloadingKey.value = file.name
  try {
    await downloadArtifact({ kind: row.kind, job_id: row.job_id, name: file.name })
  } catch (error) {
    ElMessage.error(error.message || '下载失败，请重试')
  } finally {
    downloadingKey.value = ''
  }
}

async function downloadPrimary(row) {
  if (row.kind === 'dataset') return exportDataset(row.dataset, 'csv')
  const file = row.files.find(item => /\.(csv|xlsx|zip)$/i.test(item.name)) || row.files[0]
  if (!file) return
  await downloadFile(row, file)
}

async function exportDataset(dataset, format) {
  if (libraryState.auth) return
  downloadingKey.value = dataset.dataset_id
  try {
    const batch = await exportStorageTable({ table: 'commit', format, dataset_id: dataset.dataset_id })
    const output = (batch?.outputs || []).find(item => item.name.endsWith(`.${format}`))
    if (!output) throw new Error('数据集导出未生成文件')
    const blob = await fetchStorageOutput(batch.job_id, output.name)
    saveBlob(blob, output.name)
  } catch (error) {
    ElMessage.error(error.message || '数据集导出失败')
  } finally {
    downloadingKey.value = ''
  }
}

async function removeDataset(row) {
  try {
    await ElMessageBox.confirm(
      `确认删除数据集「${row.name}」？其成员关联会一并移除，模块产物文件不受影响。`,
      '删除数据集',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  deletingKey.value = row.key
  try {
    await deleteDataset(row.dataset.dataset_id)
    ElMessage.success('已删除数据集')
    await loadLibrary()
  } catch (error) {
    ElMessage.error(error.message || '删除失败，请重试')
  } finally {
    deletingKey.value = ''
  }
}

onMounted(() => {
  loadLibrary()
  if (active.value === 'lineage') loadLineage()
})

watch(active, value => {
  if (value === 'lineage' && !lineage.items.length) loadLineage()
})
</script>

<style scoped>
.storage { min-width: 0; }
.notice { margin: var(--ui-space-3) 0; overflow-wrap: anywhere; }
.filter-control { width: 160px; }
.filter-control--wide { width: 240px; }
.table-scroll { width: 100%; min-width: 0; max-width: 100%; overflow-x: auto; }
.pagination { margin-top: var(--ui-space-3); }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: var(--ui-space-1); margin: var(--ui-space-1) 0; }
.actions :deep(.el-button + .el-button) { margin-left: 0; }
.file-list { list-style: none; padding: 0; margin: var(--ui-space-3) 0; }
.file-list li {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ui-space-2);
  padding: 4px 0;
  font-size: var(--ui-font-sm);
}
.file-name { min-width: 0; overflow-wrap: anywhere; }
.file-size { color: var(--ui-text-muted); font-size: var(--ui-font-hint); }
.result-block { margin-top: var(--ui-space-5); }
@media (max-width: 768px) {
  .filter-control, .filter-control--wide { width: 100%; }
  .field-grid { grid-template-columns: minmax(0, 1fr); }
}
</style>
