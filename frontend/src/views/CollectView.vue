<template>
  <div class="stack">
    <PageHeader title="数据收集" subtitle="从 GitHub / Gitee 仓库收集提交，SZZ 打标并生成特征" eyebrow="Pipeline 01">
      <template #actions>
        <el-button @click="confirmReset">重置</el-button>
      </template>
    </PageHeader>

    <div v-if="page.syncError" class="pill warning">进度未同步：{{ page.syncError }}</div>

    <SectionCard index="01" title="仓库与解析方式" description="只支持公开仓库，无需登录；平台限流时请稍后重试。同一数据集只允许一个仓库">
      <el-form label-position="top">
        <div class="grid-2">
          <el-form-item label="仓库地址">
            <div class="row">
              <el-input v-model="state.form.repo_url" placeholder="https://github.com/owner/repo" :disabled="running" @keyup.enter="loadBranches" />
              <el-button :loading="branchLoading" :disabled="running || !state.form.repo_url" @click="loadBranches">读取分支</el-button>
            </div>
          </el-form-item>
          <el-form-item label="分支">
            <el-select v-model="state.form.branch" filterable placeholder="先读取分支" style="width: 100%" :disabled="running || !branches.length">
              <el-option v-for="item in branches" :key="item" :value="item" :label="item" />
            </el-select>
          </el-form-item>
        </div>

        <el-form-item label="解析方式">
          <div class="mode-grid">
            <button
              class="mode"
              :class="{ active: state.form.mode === 'expert' }"
              :disabled="running"
              @click="setMode('expert')"
            >
              <strong>专家特征</strong>
              <span>Kamei 14 维 · 轻量快速</span>
            </button>
            <button
              class="mode"
              :class="{ active: state.form.mode === 'semantic' }"
              :disabled="running"
              @click="setMode('semantic')"
            >
              <strong>语义向量</strong>
              <span>CodeBERT 768 维 · 语义更丰富</span>
            </button>
          </div>
        </el-form-item>

        <div class="row wrap">
          <el-button type="primary" plain :loading="prechecking" :disabled="running || !state.form.repo_url || !state.form.branch" @click="runPrecheck">
            预检并估算耗时
          </el-button>
          <span v-if="state.precheck" class="muted">
            提交 {{ state.precheck.commit_count }} ｜ 缺陷 issue {{ state.precheck.issue_count }} ｜ 预计 {{ estimateMinutes }} 分钟
          </span>
        </div>

        <el-alert
          v-if="state.precheck && state.precheck.warn_level === 'yellow'"
          class="alert"
          type="warning"
          :closable="false"
          title="预估耗时较长"
          description="可缩小分支范围或改用专家特征，实际耗时以任务面板为准。"
        />
        <el-alert
          v-if="state.precheck && state.precheck.warn_level === 'red'"
          class="alert"
          type="error"
          :closable="false"
          title="预估耗时超出红色阈值"
          description="建议更换更小的仓库或减少时间范围，避免长时间占用任务。"
        />
        <div v-if="branchError" class="form-error">{{ branchError }}</div>
        <div v-if="precheckError" class="form-error">{{ precheckError }}</div>
      </el-form>

      <template #footer>
        <span class="muted">预检通过后即可开始；同一用户同一时刻仅允许一个运行中任务。</span>
        <el-button type="primary" :disabled="!canRun" :loading="starting" @click="startCollect">开始收集</el-button>
      </template>
    </SectionCard>

    <SectionCard v-if="job" index="02" title="执行进度" description="任务产物写入临时目录，只有点击保存才进入数据库">
      <JobPanel
        :job="job"
        :elapsed="elapsed"
        :progress="progress"
        :is-running="isRunning"
        :is-success="isSuccess"
        :is-failed="isFailed"
        @cancel="cancelJob"
      />
      <div v-if="isCancelled" class="form-error">任务已取消，本轮结果已丢弃。</div>
    </SectionCard>

    <SectionCard v-if="result" index="03" title="结果预览" description="核心字段预览；完整列请导出查看">
      <template #aside>
        <span class="pill success">正 {{ resultSummary.pos }}</span>
        <span class="pill">负 {{ resultSummary.neg }}</span>
        <span class="pill">{{ resultSummary.total }} 行</span>
      </template>

      <el-table v-loading="rowsLoading" :data="rows" border>
        <el-table-column
          v-for="column in result.columns"
          :key="column"
          :prop="column"
          :label="column"
          min-width="130"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span :class="{ mono: column === 'commit_id' }">{{ cell(row[column], column) }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination
          v-model:current-page="rowPage"
          :page-size="rowPageSize"
          :total="resultSummary.total"
          layout="prev, pager, next"
          :hide-on-single-page="true"
          @current-change="loadRows"
        />
      </div>

      <div class="export-row">
        <el-input v-model="exportName" placeholder="导出文件名（不含扩展名）" style="max-width: 260px" />
        <el-radio-group v-model="exportFormat">
          <el-radio value="csv">CSV</el-radio>
          <el-radio value="excel">Excel</el-radio>
        </el-radio-group>
        <el-button :loading="exporting" @click="doExport">导出</el-button>
      </div>

      <template #footer>
        <div class="row wrap grow">
          <span class="muted">保存后可在数据存储页下载与复用。</span>
          <el-input v-model="state.datasetName" placeholder="数据集名称" style="max-width: 240px" :disabled="state.saved" />
        </div>
        <div class="row">
          <span v-if="state.saved" class="pill success">已保存</span>
          <el-button type="primary" :loading="saving" :disabled="state.saved || !state.datasetName.trim()" @click="saveDataset">
            保存到数据库
          </el-button>
        </div>
      </template>
    </SectionCard>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import SectionCard from '../components/SectionCard.vue'
import JobPanel from '../components/JobPanel.vue'
import { saveDataset as saveDatasetApi } from '../api/datasets'
import { exportResult, getBranches, getRows, precheck, run } from '../api/collect'
import { getJob } from '../api/jobs'
import { humanError } from '../utils/format'
import { saveBlob } from '../utils/download'
import { useJob } from '../composables/useJob'
import { usePageState } from '../composables/usePageState'

const page = usePageState('collect', () => ({
  step: 1,
  form: { repo_url: '', branch: '', mode: 'expert' },
  precheck: null,
  job_id: null,
  result_ref: null,
  datasetName: '',
  saved: false
}))

const state = page.state
const branches = ref([])
const branchLoading = ref(false)
const branchError = ref('')
const prechecking = ref(false)
const precheckError = ref('')
const starting = ref(false)
const rows = ref([])
const rowsLoading = ref(false)
const rowPage = ref(1)
const rowPageSize = 20
const resultSummary = ref({ total: 0, pos: 0, neg: 0 })
const resultColumns = ref([])
const result = computed(() =>
  state.result_ref ? { job_id: state.result_ref.job_id, columns: resultColumns.value } : null
)
const exportName = ref('')
const exportFormat = ref('csv')
const exporting = ref(false)
const saving = ref(false)

const { job, elapsed, progress, isRunning, isSuccess, isFailed, isCancelled, track, cancel, reset: resetJob } = useJob()

const estimateMinutes = computed(() => {
  const seconds = state.precheck?.estimate_seconds || 0
  return Math.max(1, Math.ceil(seconds / 60))
})

const canRun = computed(() =>
  state.form.repo_url && state.form.branch && state.precheck && !running.value && !starting.value
)

const running = computed(() => isRunning.value)

function setMode(mode) {
  if (state.form.mode === mode) return
  state.form.mode = mode
  state.precheck = null
  if (state.form.repo_url && state.form.branch) runPrecheck()
}

function cell(value, column) {
  if (value === null || value === undefined || value === '') return '—'
  if (column === 'bug') return Number(value) === 1 ? '缺陷' : '正常'
  if (typeof value === 'number') return Number(value.toFixed(4))
  return String(value)
}

async function loadBranches() {
  if (!state.form.repo_url) return
  branchLoading.value = true
  branchError.value = ''
  branches.value = []
  try {
    const data = await getBranches(state.form.repo_url)
    branches.value = data.branches || []
    if (!data.branches.includes(state.form.branch)) state.form.branch = data.default_branch || data.branches[0] || ''
    state.precheck = null
  } catch (requestError) {
    branchError.value = humanError(requestError)
  } finally {
    branchLoading.value = false
  }
}

async function runPrecheck() {
  prechecking.value = true
  precheckError.value = ''
  try {
    state.precheck = await precheck(state.form.repo_url, state.form.branch, state.form.mode)
    state.step = 2
  } catch (requestError) {
    state.precheck = null
    precheckError.value = humanError(requestError)
  } finally {
    prechecking.value = false
  }
}

async function startCollect() {
  if (!canRun.value) return
  starting.value = true
  precheckError.value = ''
  state.result_ref = null
  state.job_id = null
  resultColumns.value = []
  state.saved = false
  state.datasetName = state.datasetName || defaultName()
  try {
    const data = await run({ repo_url: state.form.repo_url, branch: state.form.branch, mode: state.form.mode })
    state.job_id = data.job_id
    state.step = 3
    track(data.job_id, data.total || 0)
  } catch (requestError) {
    precheckError.value = humanError(requestError)
  } finally {
    starting.value = false
  }
}

function defaultName() {
  const repo = (state.form.repo_url || '').replace(/\.git$/, '').split('/').slice(-2).join('-')
  return `${repo}-${state.form.branch}-${state.form.mode}`
}

async function cancelJob() {
  try {
    await ElMessageBox.confirm('确认取消当前收集任务？本轮未保存结果将被丢弃。', '取消任务', {
      type: 'warning',
      confirmButtonText: '取消任务',
      cancelButtonText: '继续等待'
    })
    await cancel()
  } catch (requestError) {
    if (requestError !== 'cancel') ElMessage.error(humanError(requestError))
  }
}

async function loadRows() {
  if (!state.result_ref?.job_id) return
  rowsLoading.value = true
  try {
    const data = await getRows(state.result_ref.job_id, { page: rowPage.value, page_size: rowPageSize })
    rows.value = data.items
    resultColumns.value = data.columns
    resultSummary.value = data.summary
  } catch (requestError) {
    ElMessage.error(humanError(requestError))
  } finally {
    rowsLoading.value = false
  }
}

function applySuccess() {
  if (!job.value?.job_id) return
  state.job_id = job.value.job_id
  state.result_ref = { job_id: job.value.job_id, kind: 'collect' }
  state.step = 3
  resultColumns.value = []
  state.datasetName = state.datasetName || defaultName()
  exportName.value = `${defaultName()}-${job.value.job_id.slice(4, 12)}`
  resultSummary.value = { total: job.value.total, pos: 0, neg: 0 }
  rowPage.value = 1
  loadRows()
}

watch(
  () => job.value?.status,
  async (value) => {
    if (value === 'success') applySuccess()
    if (value === 'failed' && job.value?.error_message) ElMessage.error(job.value.error_message)
  }
)

async function doExport() {
  if (!state.result_ref?.job_id) return
  if (!exportName.value.trim()) {
    ElMessage.error('文件名不能为空')
    return
  }
  exporting.value = true
  try {
    const response = await exportResult(state.result_ref.job_id, {
      filename: exportName.value.trim(),
      format: exportFormat.value
    })
    saveBlob(response, `${exportName.value.trim()}.${exportFormat.value === 'excel' ? 'xlsx' : 'csv'}`)
  } catch (requestError) {
    ElMessage.error(humanError(requestError))
  } finally {
    exporting.value = false
  }
}

async function saveDataset() {
  if (!state.result_ref?.job_id) return
  saving.value = true
  try {
    await saveDatasetApi(state.result_ref.job_id, state.datasetName.trim())
    state.saved = true
    ElMessage.success('数据集已保存')
  } catch (requestError) {
    ElMessage.error(humanError(requestError))
  } finally {
    saving.value = false
  }
}

async function confirmReset() {
  try {
    await ElMessageBox.confirm('重置会清空本页进度与未保存结果，已保存资产不受影响。', '重置页面', {
      type: 'warning',
      confirmButtonText: '重置',
      cancelButtonText: '取消'
    })
  } catch (error) {
    return
  }
  resetJob()
  branches.value = []
  rows.value = []
  resultSummary.value = { total: 0, pos: 0, neg: 0 }
  rowPage.value = 1
  await page.reset()
}

async function restore() {
  if (state.form.repo_url && !branches.value.length) {
    loadBranches()
  }
  if (!state.result_ref?.job_id) return
  try {
    const data = await getJob(state.result_ref.job_id)
    if (data.status === 'success') {
      job.value = data
      applySuccess()
    } else if (['queued', 'running'].includes(data.status)) {
      state.job_id = data.job_id
      track(data.job_id, data.total)
    } else {
      state.result_ref = null
      state.job_id = null
    }
  } catch (error) {
    state.result_ref = null
    state.job_id = null
  }
}

onMounted(async () => {
  await page.ready
  await restore()
  if (!exportName.value) exportName.value = `${defaultName()}-${Date.now().toString().slice(-6)}`
})
</script>

<style scoped>
.mode-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  width: 100%;
}

.mode {
  text-align: left;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-muted);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: 0.16s ease;
}

.mode strong {
  font-size: 13.5px;
}

.mode span {
  font-size: 12px;
  color: var(--text-muted);
}

.mode.active {
  border-color: rgba(15, 118, 110, 0.45);
  background: var(--primary-soft);
  box-shadow: 0 8px 20px rgba(15, 118, 110, 0.08);
}

.alert {
  margin-top: 12px;
}

.form-error {
  color: var(--danger);
  font-size: 12.5px;
  margin-top: 8px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

.export-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed var(--border);
}

@media (max-width: 768px) {
  .mode-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
