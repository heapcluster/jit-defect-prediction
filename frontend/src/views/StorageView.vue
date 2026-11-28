<template>
  <div class="stack">
    <PageHeader title="数据存储" subtitle="当前用户的数据、模型与配置中心" eyebrow="Workspace">
      <template #actions>
        <el-button :loading="loading" @click="refresh">刷新</el-button>
        <el-button @click="handleLogout">登出</el-button>
      </template>
    </PageHeader>

    <div v-if="page.syncError" class="pill warning">进度未同步：{{ page.syncError }}</div>

    <section class="user-strip">
      <div class="user-main">
        <div class="avatar">{{ initials }}</div>
        <div>
          <div class="user-title">{{ session.user?.display_name || '—' }}</div>
          <div class="user-sub mono">{{ session.user?.username || '—' }}</div>
        </div>
      </div>
      <div class="user-metrics">
        <div><span>数据集</span><strong>{{ session.counts.datasets ?? '—' }}</strong></div>
        <div><span>模型</span><strong>{{ session.counts.models ?? '—' }}</strong></div>
        <div><span>最近登录</span><strong class="time">{{ formatTime(session.lastLoginAt) }}</strong></div>
      </div>
    </section>

    <div class="segments" role="tablist">
      <button
        v-for="item in sections"
        :key="item.key"
        class="segment"
        :class="{ active: section === item.key }"
        role="tab"
        :aria-selected="section === item.key"
        @click="switchSection(item.key)"
      >
        {{ item.label }}
      </button>
    </div>

    <template v-if="section === 'files'">
      <StatStrip :items="fileStats" />

      <SectionCard title="我的文件" description="按生成时间倒序；数据集与模型可独立下载与删除">
        <template #aside>
          <el-button size="small" :loading="loading" @click="loadFiles">刷新</el-button>
        </template>

        <div class="filters">
          <el-select v-model="filters.type" style="width: 130px" @change="resetPage(files)">
            <el-option label="全部类型" value="" />
            <el-option label="数据集" value="dataset" />
            <el-option label="模型" value="model" />
          </el-select>
          <el-select v-model="filters.tag" clearable placeholder="全部标签" style="width: 150px" @change="resetPage(files)">
            <el-option label="原始" value="git_repo" />
            <el-option label="导入清洗" value="upload" />
            <el-option label="清洗" value="clean" />
            <el-option label="测试集" value="split" />
            <el-option label="预测结果" value="prediction" />
            <el-option label="专家特征" value="expert" />
            <el-option label="语义向量" value="semantic" />
          </el-select>
          <el-select v-model="filters.status" style="width: 130px" @change="resetPage(files)">
            <el-option label="全部状态" value="" />
            <el-option label="可用" value="available" />
            <el-option label="异常" value="failed" />
            <el-option label="文件缺失" value="missing" />
          </el-select>
          <el-input v-model="filters.q" clearable placeholder="搜索名称或任务号" style="width: 210px" @keyup.enter="resetPage(files)" @clear="resetPage(files)" />
          <el-button @click="resetPage(files)">查询</el-button>
        </div>

        <div v-if="files.error" class="stack">
          <ErrorState :message="files.error" @retry="loadFiles" />
        </div>
        <EmptyState
          v-else-if="!loading && !files.items.length"
          title="还没有保存的数据资产"
          description="在数据收集、清洗、训练或预测页点击保存后，资产会出现在这里。"
        >
          <template #action>
            <el-button type="primary" @click="$router.push('/collect')">去收集</el-button>
          </template>
        </EmptyState>
        <template v-else>
          <el-table v-loading="loading" :data="files.items" border>
            <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
            <el-table-column label="类型" width="92">
              <template #default="{ row }">
                <span class="pill">{{ row.type === 'dataset' ? '数据集' : '模型' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="标签" width="116">
              <template #default="{ row }">
                <span class="pill primary">{{ badgeOf(row) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="来源任务" width="140">
              <template #default="{ row }">
                <span class="mono soft">{{ shortId(row.source_job_id) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="生成时间" width="180">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" effect="light" round>{{ STATUS[row.status] || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="210" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="openAsset(row)">查看</el-button>
                <el-button link @click="startDownload(row)">下载</el-button>
                <el-button link type="danger" @click="confirmDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pager">
            <el-pagination
              v-model:current-page="files.page"
              v-model:page-size="files.page_size"
              :total="files.total"
              :page-sizes="[10, 20, 50]"
              layout="total, sizes, prev, pager, next"
              :hide-on-single-page="true"
              @current-change="loadFiles"
              @size-change="resetPage(files)"
            />
          </div>
        </template>
      </SectionCard>
    </template>

    <template v-else-if="section === 'algorithms'">
      <SectionCard title="算法库" description="只读清单，来自数据库 algorithm 表，训练页按模型线读取同一份配置">
        <template #aside>
          <el-select v-model="algoFilters.line" style="width: 150px" @change="loadAlgorithms">
            <el-option label="全部模型线" value="" />
            <el-option label="专家特征" value="expert" />
            <el-option label="语义向量" value="semantic" />
          </el-select>
          <el-input v-model="algoFilters.q" clearable placeholder="搜索算法" style="width: 170px" @keyup.enter="loadAlgorithms" @clear="loadAlgorithms" />
        </template>

        <div v-if="algoError"><ErrorState :message="algoError" @retry="loadAlgorithms" /></div>
        <el-table v-else v-loading="algoLoading" :data="algorithms" border>
          <el-table-column prop="algo" label="算法" width="120">
            <template #default="{ row }"><span class="mono strong">{{ row.algo }}</span></template>
          </el-table-column>
          <el-table-column label="模型线" width="120">
            <template #default="{ row }">{{ LINE[row.line] || row.line }}</template>
          </el-table-column>
          <el-table-column prop="family" label="类别" width="130" />
          <el-table-column label="可训练" width="100">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'" effect="light" round>{{ row.enabled ? '是' : '否' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="180" />
        </el-table>
      </SectionCard>
    </template>

    <template v-else>
      <SectionCard title="我的配置" description="耗时提醒阈值只影响预估提示，不改变任务实际执行">
        <div v-if="configError"><ErrorState :message="configError" @retry="loadConfig" /></div>
        <el-form v-else v-loading="configLoading" label-position="top" class="config-form">
          <div class="grid-2">
            <el-form-item label="预估黄色提醒（分钟）">
              <el-input-number v-model="configForm.warn" :min="1" :max="1440" :controls="false" style="width: 100%" />
            </el-form-item>
            <el-form-item label="预估红色提醒（分钟）">
              <el-input-number v-model="configForm.danger" :min="1" :max="1440" :controls="false" style="width: 100%" />
            </el-form-item>
          </div>
          <p v-if="configForm.warn >= configForm.danger" class="form-error">黄色阈值必须小于红色阈值。</p>
          <div class="row">
            <el-button type="primary" :loading="configSaving" :disabled="configForm.warn >= configForm.danger" @click="saveConfigForm">
              保存配置
            </el-button>
            <span v-if="configSaved" class="pill success">已保存</span>
          </div>
        </el-form>
      </SectionCard>
    </template>

    <el-dialog v-model="downloadDialog" title="下载数据集" width="420px">
      <el-form label-position="top">
        <el-form-item label="文件名">
          <el-input v-model="downloadForm.filename" placeholder="不含扩展名" />
        </el-form-item>
        <el-form-item label="格式">
          <el-radio-group v-model="downloadForm.format">
            <el-radio value="csv">CSV</el-radio>
            <el-radio value="excel">Excel</el-radio>
          </el-radio-group>
        </el-form-item>
        <p v-if="downloadError" class="form-error">{{ downloadError }}</p>
      </el-form>
      <template #footer>
        <el-button @click="downloadDialog = false">取消</el-button>
        <el-button type="primary" :loading="downloading" @click="doDownload">下载</el-button>
      </template>
    </el-dialog>

    <AssetDrawer v-model="drawerOpen" :asset="activeAsset" @download="startDownload" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import SectionCard from '../components/SectionCard.vue'
import StatStrip from '../components/StatStrip.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'
import AssetDrawer from '../components/AssetDrawer.vue'
import { deleteDataset } from '../api/datasets'
import {
  deleteModel,
  downloadAsset,
  getConfig,
  listAlgorithms,
  listFiles,
  saveConfig
} from '../api/storage'
import { humanError, formatTime, LINE, shortId, SOURCE_TYPE, STATUS, statusType } from '../utils/format'
import { saveBlob } from '../utils/download'
import { clearSession, loadSession, session, signOut } from '../stores/session'
import { usePageState } from '../composables/usePageState'

const route = useRoute()
const router = useRouter()
const page = usePageState('storage', () => ({ section: 'files' }))
const state = page.state

const sections = [
  { key: 'files', label: '我的文件' },
  { key: 'algorithms', label: '算法库' },
  { key: 'config', label: '我的配置' }
]

const section = ref(normalizeSection(route.query.section))
const loading = ref(false)
const files = reactive({ items: [], total: 0, page: 1, page_size: 20, error: '' })
const filters = reactive({ type: '', tag: '', status: '', q: '' })

const algorithms = ref([])
const algoLoading = ref(false)
const algoError = ref('')
const algoFilters = reactive({ line: '', q: '' })

const configForm = reactive({ warn: 10, danger: 30 })
const configLoading = ref(false)
const configError = ref('')
const configSaving = ref(false)
const configSaved = ref(false)

const drawerOpen = ref(false)
const activeAsset = ref(null)
const downloadDialog = ref(false)
const downloading = ref(false)
const downloadError = ref('')
const downloadForm = reactive({ filename: '', format: 'csv', asset: null })

const initials = computed(() => {
  const name = session.user?.display_name || session.user?.username || 'J'
  return name.slice(0, 1).toUpperCase()
})

const fileStats = computed(() => {
  const datasets = files.items.filter((item) => item.type === 'dataset').length
  const models = files.items.filter((item) => item.type === 'model').length
  return [
    { label: '数据集', value: session.counts.datasets ?? '—', tone: 'primary' },
    { label: '模型', value: session.counts.models ?? '—', tone: 'accent' },
    { label: '当前页资产', value: files.total, hint: `数据集 ${datasets} · 模型 ${models}` }
  ]
})

function normalizeSection(value) {
  return ['files', 'algorithms', 'config'].includes(value) ? value : 'files'
}

function badgeOf(row) {
  return row.type === 'dataset' ? SOURCE_TYPE[row.badge] || row.badge : LINE[row.badge] || row.badge
}

function switchSection(key) {
  section.value = key
  state.section = key
  const query = { ...route.query, section: key }
  router.replace({ path: '/storage', query })
}

watch(
  () => route.query.section,
  (value) => {
    section.value = normalizeSection(value)
    state.section = section.value
    onSection()
  }
)

function resetPage(target) {
  target.page = 1
  loadFiles()
}

async function loadFiles() {
  loading.value = true
  files.error = ''
  try {
    const params = {
      type: filters.type || undefined,
      source_type: SOURCE_TYPE[filters.tag] ? filters.tag : undefined,
      line: LINE[filters.tag] ? filters.tag : undefined,
      status: filters.status === 'available' ? undefined : filters.status || undefined,
      q: filters.q || undefined,
      page: files.page,
      page_size: files.page_size
    }
    const data = await listFiles(params)
    files.items = data.items
    files.total = data.total
  } catch (error) {
    files.error = humanError(error)
  } finally {
    loading.value = false
  }
}

async function loadAlgorithms() {
  algoLoading.value = true
  algoError.value = ''
  try {
    const data = await listAlgorithms({ line: algoFilters.line || undefined, q: algoFilters.q || undefined })
    algorithms.value = data.items
  } catch (error) {
    algoError.value = humanError(error)
  } finally {
    algoLoading.value = false
  }
}

async function loadConfig() {
  configLoading.value = true
  configError.value = ''
  configSaved.value = false
  try {
    const data = await getConfig()
    configForm.warn = data.items.estimate_warn_minutes ?? 10
    configForm.danger = data.items.estimate_danger_minutes ?? 30
  } catch (error) {
    configError.value = humanError(error)
  } finally {
    configLoading.value = false
  }
}

async function saveConfigForm() {
  if (configForm.warn >= configForm.danger) return
  configSaving.value = true
  try {
    await saveConfig({
      estimate_warn_minutes: configForm.warn,
      estimate_danger_minutes: configForm.danger
    })
    configSaved.value = true
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error(humanError(error))
  } finally {
    configSaving.value = false
  }
}

function onSection() {
  if (section.value === 'files') loadFiles()
  else if (section.value === 'algorithms') loadAlgorithms()
  else loadConfig()
}

async function refresh() {
  await loadSession(true)
  onSection()
}

function openAsset(row) {
  activeAsset.value = row
  drawerOpen.value = true
}

function startDownload(row) {
  if (row.type === 'model') {
    downloadModel(row)
    return
  }
  downloadError.value = ''
  downloadForm.asset = row
  downloadForm.filename = row.name
  downloadForm.format = 'csv'
  downloadDialog.value = true
}

async function downloadModel(row) {
  try {
    const response = await downloadAsset(row.id, {})
    saveBlob(response, `${row.name}.${row.format || 'pkl'}`)
  } catch (error) {
    ElMessage.error(humanError(error))
  }
}

async function doDownload() {
  downloadError.value = ''
  if (!downloadForm.filename.trim()) {
    downloadError.value = '文件名不能为空'
    return
  }
  downloading.value = true
  try {
    const response = await downloadAsset(downloadForm.asset.id, {
      filename: downloadForm.filename.trim(),
      format: downloadForm.format
    })
    saveBlob(response, `${downloadForm.filename.trim()}.${downloadForm.format === 'excel' ? 'xlsx' : 'csv'}`)
    downloadDialog.value = false
  } catch (error) {
    downloadError.value = humanError(error)
  } finally {
    downloading.value = false
  }
}

async function confirmDelete(row) {
  const detail = row.type === 'dataset'
    ? `样本 ${row.sample_count ?? '—'} 条，删除后不可恢复。`
    : `算法 ${row.algo || '—'}，删除后模型文件一并移除。`
  try {
    await ElMessageBox.confirm(`确认删除「${row.name}」？${detail}`, '删除资产', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  try {
    if (row.type === 'dataset') await deleteDataset(row.id)
    else await deleteModel(row.id)
    ElMessage.success('已删除')
    await refresh()
  } catch (error) {
    ElMessage.error(humanError(error))
  }
}

async function handleLogout() {
  await signOut()
  clearSession()
  router.replace('/login')
}

onMounted(async () => {
  await page.ready
  const routeSection = route.query.section
  section.value = normalizeSection(routeSection || state.section)
  state.section = section.value
  if (!routeSection && section.value !== 'files') {
    router.replace({ path: '/storage', query: { ...route.query, section: section.value } })
  }
  await loadSession(true)
  onSection()
})
</script>

<style scoped>
.user-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 16px 20px;
  border-radius: var(--radius-lg);
  background: linear-gradient(120deg, #0b1220, #12253c);
  color: #e2e8f0;
  box-shadow: var(--shadow);
  flex-wrap: wrap;
}

.user-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-weight: 800;
  color: #06201d;
  background: linear-gradient(135deg, #93c5fd, #5eead4);
}

.user-title {
  font-weight: 700;
  font-size: 15px;
  color: #f8fafc;
}

.user-sub {
  color: rgba(148, 163, 184, 0.9);
}

.user-metrics {
  display: flex;
  gap: 26px;
  flex-wrap: wrap;
}

.user-metrics > div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.user-metrics span {
  font-size: 11px;
  color: rgba(148, 163, 184, 0.85);
  letter-spacing: 0.04em;
}

.user-metrics strong {
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.user-metrics .time {
  font-size: 12.5px;
  font-weight: 600;
  color: #cbd5e1;
}

.segments {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  width: fit-content;
  box-shadow: var(--shadow-sm);
}

.segment {
  border: 0;
  background: transparent;
  padding: 8px 16px;
  border-radius: 9px;
  font-weight: 650;
  font-size: 13px;
  color: var(--text-muted);
  cursor: pointer;
}

.segment.active {
  background: var(--primary);
  color: white;
}

.filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.config-form {
  max-width: 620px;
}

.form-error {
  color: var(--danger);
  font-size: 12.5px;
  margin: -4px 0 12px;
}

.strong {
  font-weight: 700;
}
</style>
