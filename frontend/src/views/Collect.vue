<template>
  <section class="collect-tool">
    <ToolWorkspace
      hide-tabs
      model-value="collect"
    >
      <template #collect>
        <el-alert
          v-if="error"
          :title="error"
          type="error"
          :closable="false"
          show-icon
        />
        <StepRail
          :steps="railSteps"
          :active="activeStep"
        />
        <StepSection
          index="01"
          title="选择来源"
          :state="stepState(0)"
          collapsible
          :summary="source === 'git' ? repoName : (publicDraft.name.trim() || '开源数据集')"
        >
          <template #extra>
            <el-tag
              v-if="sourceReady"
              size="small"
              type="success"
            >
              {{ source === 'git' ? '已连接' : '已解析' }}
            </el-tag>
          </template>
          <ChoiceGroup
            :model-value="source"
            name="collect-source"
            :options="sourceChoices"
            :disabled="busy || auth || isRunning"
            stack
            @change="setSource"
          />
          <div
            v-if="source === 'git'"
            class="source-fields"
          >
            <div class="fields">
              <div class="field">
                <span class="field-label">仓库路径或地址</span>
                <div class="field-line">
                  <el-input
                    id="collect-repo"
                    v-model="draft.repo_source"
                    :disabled="busy || auth || isRunning"
                    aria-label="仓库路径"
                    autocomplete="off"
                    placeholder="/path/to/repo 或 https://..."
                    @input="checkRepo"
                  />
                  <span class="field-hint">本地路径或 URL</span>
                </div>
              </div>
              <div class="field">
                <span class="field-label">分支</span>
                <div class="field-line">
                  <el-select
                    id="collect-branch"
                    v-model="draft.branch"
                    :placeholder="branchesLoading ? '正在读取分支…' : branches.length ? '请选择分支' : '先刷新分支'"
                    :disabled="busy || auth || isRunning || !branches.length"
                  >
                    <el-option
                      v-for="branch in branches"
                      :key="branch"
                      :label="branch"
                      :value="branch"
                    />
                  </el-select>
                  <el-button
                    :loading="branchesLoading"
                    :disabled="!draft.repo_source.trim() || busy || auth || isRunning"
                    @click="loadBranches"
                  >
                    刷新分支
                  </el-button>
                </div>
              </div>
              <p
                v-if="branchError"
                class="validation"
              >
                {{ branchError }}
              </p>
            </div>
            <InfoGrid
              v-if="repoReady"
              :items="repoInfo"
            />
          </div>
          <div
            v-else
            class="source-fields"
          >
            <div class="fields">
              <div class="field">
                <span class="field-label">数据集名称</span>
                <el-input
                  id="public-name"
                  v-model="publicDraft.name"
                  :disabled="busy || auth || isRunning"
                  aria-label="数据集名称"
                  placeholder="数据集名称"
                />
              </div>
              <div class="field">
                <span class="field-label">公开数据集 URL</span>
                <div class="field-line">
                  <el-input
                    id="public-url"
                    v-model="publicDraft.source_url"
                    :disabled="busy || auth || isRunning"
                    aria-label="公开数据集 URL"
                    placeholder="https://.../dataset.csv"
                  />
                  <el-button
                    :loading="columnsLoading"
                    :disabled="!publicDraft.source_url.trim() || busy || auth || isRunning"
                    @click="loadPublicColumns"
                  >
                    读取字段
                  </el-button>
                </div>
              </div>
              <div class="field">
                <span class="field-label">许可证（可选）</span>
                <el-input
                  id="public-license"
                  v-model="publicDraft.license"
                  :disabled="busy || auth || isRunning"
                  aria-label="许可证"
                  placeholder="如 Apache-2.0"
                />
              </div>
              <p
                v-if="columnsError"
                class="validation"
              >
                {{ columnsError }}
              </p>
            </div>
          </div>
        </StepSection>

        <StepSection
          index="02"
          :title="source === 'git' ? '配置范围' : '检查列名'"
          :state="stepState(1)"
          collapsible
          :summary="source === 'git' ? rangeText : `${mappingCount} 项列映射`"
        >
          <div v-if="source === 'git'">
            <div class="field">
              <el-date-picker
                id="collect-range"
                v-model="dateRange"
                type="daterange"
                value-format="YYYY-MM-DD"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                aria-label="提交时间范围"
                :editable="false"
                :clearable="true"
                :disabled="busy || auth || isRunning"
              />
            </div>
            <p class="field-hint">
              留空表示采集仓库全量历史提交；选择日期可只采集该区间。
            </p>
            <p
              v-if="rangeError"
              class="validation"
            >
              {{ rangeError }}
            </p>
          </div>
          <div v-else>
            <div class="fields mapping-fields">
              <div
                v-for="field in mappingFields"
                :key="field.key"
                class="field"
                :class="{ 'field-invalid': mappingIssues.includes(field.label) }"
              >
                <span class="field-label">
                  {{ field.label }}<span
                    v-if="field.required"
                    class="field-required"
                  >*</span>
                </span>
                <el-select
                  :id="`public-map-${field.key}`"
                  v-model="publicDraft.mapping[field.key]"
                  :aria-label="field.label"
                  :placeholder="publicColumns.length ? '选择对应列' : '先读取字段'"
                  filterable
                  clearable
                  :disabled="!publicColumns.length || busy || auth || isRunning"
                >
                  <el-option
                    v-for="column in publicColumns"
                    :key="column"
                    :label="column"
                    :value="column"
                  />
                </el-select>
              </div>
              <div class="field">
                <span class="field-label">有缺陷取值</span>
                <el-input
                  id="public-label-yes"
                  v-model="publicDraft.label_yes"
                  aria-label="有缺陷"
                  :disabled="!publicColumns.length || busy || auth || isRunning"
                />
              </div>
              <div class="field">
                <span class="field-label">无缺陷取值</span>
                <el-input
                  id="public-label-no"
                  v-model="publicDraft.label_no"
                  aria-label="无缺陷"
                  :disabled="!publicColumns.length || busy || auth || isRunning"
                />
              </div>
            </div>
            <p
              v-if="mappingIssues.length"
              class="validation"
            >
              未匹配必填列：{{ mappingIssues.join('、') }}
            </p>
          </div>
        </StepSection>

        <StepSection
          index="03"
          title="确认导出文件名称"
          :state="stepState(2)"
          collapsible
          :summary="datasetName.trim() || '尚未命名'"
        >
          <div class="field">
            <span class="field-label">数据集名称</span>
            <el-input
              id="collect-dataset-name"
              v-model="datasetName"
              aria-label="数据集名称"
              placeholder="请输入数据集名称"
              :disabled="!sourceReady || busy || auth || isRunning"
            />
          </div>
          <InfoGrid :items="confirmInfo" />
        </StepSection>
        <StepSection
          index="04"
          title="运行"
          :state="stepState(3)"
          sticky
        >
          <el-button
            class="run-button"
            data-testid="collect-run"
            type="primary"
            size="large"
            :loading="busy"
            :disabled="!canRun || busy || auth || isRunning"
            @click="submit"
          >
            开始收集
          </el-button>
        </StepSection>
      </template>
      <template #after>
        <JobProgress
          title="收集进度"
          test-id="collect-job"
          :job="collection.job"
          :text="progressText"
          retry-test-id="collect-retry"
          cancel-test-id="collect-cancel"
          :retry-disabled="jobLoading || auth"
          :cancel-disabled="jobLoading || auth"
          @retry="retry"
          @cancel="cancel"
        />
        <section
          class="panel"
          data-pane="wide"
          aria-label="收集结果"
          data-testid="collect-result"
        >
          <div class="section-heading">
            <h2>收集结果</h2>
          </div>
          <StatGrid :items="summaryStats" />
          <p
            v-for="warning in result?.summary?.warnings || []"
            :key="warning"
            class="validation"
          >
            {{ warning }}
          </p>
          <el-alert
            v-if="previewError"
            :title="previewError"
            type="error"
            :closable="false"
          />
          <InfoGrid
            v-if="result"
            :items="[
              { label: '保存状态', value: saveMessage || (saving ? '正在保存到数据集库' : '尚未保存') },
              { label: '数据集库', value: '', key: 'dataset-save' }
            ]"
          >
            <template #dataset-save>
              <el-button
                size="small"
                :loading="saving"
                :disabled="saving || auth"
                @click="saveAutomatically"
              >
                保存到数据集库
              </el-button>
            </template>
          </InfoGrid>
          <el-collapse v-model="openResultSections">
            <el-collapse-item
              title="提交预览"
              name="preview"
            >
              <DataTable
                v-if="collectRows.length"
                test-id="collect-preview"
                :columns="collectColumns"
                :rows="collectRows"
              />
              <el-pagination
                v-if="collection.preview?.total"
                class="pagination"
                background
                layout="total, prev, pager, next"
                :current-page="previewPage"
                :page-size="previewSize"
                :total="collection.preview.total"
                hide-on-single-page
                @current-change="loadPreview"
              />
            </el-collapse-item>
          </el-collapse>
        </section>
        <section
          class="panel"
          data-pane="wide"
          aria-label="结果文件"
          data-testid="collect-files"
        >
          <div class="section-heading">
            <h2>结果文件</h2>
          </div>
          <OutputFiles
            :items="collectFiles"
            @download="item => download(item.name)"
          />
        </section>
      </template>
    </ToolWorkspace>
  </section>
</template>

<script setup>
import { computed, onActivated, onDeactivated, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ToolWorkspace from '../components/ToolWorkspace.vue'
import DataTable from '../components/DataTable.vue'
import ChoiceGroup from '../components/ChoiceGroup.vue'
import InfoGrid from '../components/InfoGrid.vue'
import JobProgress from '../components/JobProgress.vue'
import OutputFiles from '../components/OutputFiles.vue'
import StatGrid from '../components/StatGrid.vue'
import StepRail from '../components/StepRail.vue'
import StepSection from '../components/StepSection.vue'
import { cancelJob, fetchCollectOutput, getCollectBranches, getCollectPreview, getCollectSourceColumns, getJob, getJobs, resaveCollect, retryJob, runCollect } from '../api'
import { collection } from '../utils/collect'
import { saveBlob } from '../utils/download'
import { scrollToResults } from '../utils/scroll'
import { configuration } from '../utils/thresholds'

defineOptions({ name: 'CollectTool' })
const route = useRoute(), router = useRouter()
// 收集支持 Git 仓库与公开数据集 URL 两种模式，均交付同一 collected_commits 契约。
const source = ref('git')
const draft = reactive({ repo_source: '', branch: '', start_time: '', end_time: '' })
const branches = ref([]), branchesLoading = ref(false), branchError = ref('')
const dateRange = ref([])
const repoError = ref('')
const mappingFields = [
  { key: 'commit_hash', label: '提交哈希', required: true },
  { key: 'committed_at', label: '提交时间', required: true },
  { key: 'is_bug_inducing', label: '缺陷标签', required: true },
  { key: 'author_name', label: '作者' },
  { key: 'message', label: '提交说明' },
  { key: 'parent_hash', label: '父提交' }
]
const commonColumns = {
  commit_hash: ['commit_hash', 'hash', 'commit', 'commit_id', 'sha'],
  committed_at: ['committed_at', 'date', 'time', 'commit_time', 'timestamp'],
  is_bug_inducing: ['is_bug_inducing', 'label', 'bug', 'buggy', 'is_bug', 'target'],
  author_name: ['author', 'author_name', 'developer'],
  message: ['message', 'msg', 'commit_message'],
  parent_hash: ['parent_hash', 'parent', 'parents']
}
const publicDraft = reactive({
  name: '', source_url: '', license: '', label_yes: '1', label_no: '0',
  mapping: { commit_hash: '', committed_at: '', is_bug_inducing: '', author_name: '', message: '', parent_hash: '' }
})
const publicColumns = ref([]), mappingIssues = ref([])
const columnsLoading = ref(false), columnsError = ref('')
const publicReady = computed(() => Boolean(publicDraft.source_url.trim()) && Boolean(publicDraft.name.trim())
  && publicColumns.value.length > 0 && !mappingIssues.value.length)
const repoReady = computed(() => Boolean(draft.repo_source.trim()) && !repoError.value)
const repoName = computed(() => draft.repo_source.trim().split(/[\\/]/).filter(Boolean).pop() || '仓库')
const sourceReady = computed(() => source.value === 'git' ? repoReady.value : publicReady.value)
const mappingCount = computed(() => Object.values(publicDraft.mapping).filter(Boolean).length)
const sourceChoices = [
  { key: 'git', label: 'Git 仓库', note: '从本地路径或仓库地址采集提交' },
  { key: 'public', label: '开源数据集', note: '从公开数据集 URL 拉取已打标数据' }
]
const repoInfo = computed(() => [
  { label: '仓库名称', value: repoName.value },
  { label: '分支', value: draft.branch || '默认分支（HEAD）' },
  { label: '仓库路径', value: draft.repo_source.trim(), mono: true, span: true }
])
const confirmInfo = computed(() => {
  const rows = [
    { label: '数据来源', value: source.value === 'git' ? 'Git 仓库' : '开源数据集' },
    {
      label: source.value === 'git' ? '仓库路径' : '数据 URL',
      value: source.value === 'git' ? draft.repo_source.trim() : (publicDraft.source_url.trim() || '未填写'),
      mono: true
    }
  ]
  if (source.value === 'git') {
    rows.push(
      { label: '分支', value: draft.branch || '默认分支' },
      { label: '提交时间', value: rangeText.value }
    )
  } else {
    rows.push({ label: '列映射', value: `${mappingCount.value} 项` })
  }
  rows.push(
    { label: '数据集名称', value: datasetName.value || '未命名' },
    { label: '输出', value: '带标注的提交数据' },
    { label: '保存方式', value: '任务成功后自动保存到数据集库', span: true }
  )
  return rows
})
const rangeText = computed(() => {
  if (!draft.start_time && !draft.end_time) return '全量提交'
  return `${draft.start_time || '不限'} 至 ${draft.end_time || '不限'}`
})
const datasetName = ref('')
const rangeError = computed(() => source.value === 'git' && draft.start_time && draft.end_time && draft.start_time >= draft.end_time ? '结束日期必须晚于开始日期' : '')
const canRun = computed(() => sourceReady.value
  && (source.value !== 'git' || Boolean(draft.branch))
  && Boolean(datasetName.value.trim()) && !rangeError.value)
// 顶部步骤轨道跟随来源类型切换第二步文案，用户始终看到当前所处的配置环节。
const railSteps = computed(() => [
  { title: '选择来源', note: source.value === 'git' ? 'Git 仓库' : '开源数据集' },
  { title: source.value === 'git' ? '配置范围' : '检查列名', note: source.value === 'git' ? '分支与时间' : '字段映射' },
  { title: '命名输出', note: '数据集名称' },
  { title: '运行', note: '开始采集' }
])
const activeStep = computed(() => {
  if (isRunning.value) return 3
  if (collection.job?.status === 'success') return 3
  if (!sourceReady.value) return 0
  if (source.value === 'git' ? !draft.branch : mappingIssues.value.length) return 1
  return 2
})
function stepState(index) {
  if (collection.job?.status === 'success') return 'done'
  if (index < activeStep.value) return 'done'
  return index === activeStep.value ? 'current' : 'upcoming'
}
const importDraft = reactive({ name: '', repo_source: '' })
const busy = ref(false), error = ref(''), auth = ref(false), jobLoading = ref(false)
const previewError = ref(''), downloading = ref(false), saving = ref(false), saveMessage = ref('')
const previewPage = ref(1)
const previewSize = 12
const openResultSections = ref([])
let timer, mounted = true, jobEpoch = 0, autoSaveJobId = '', lastNameDefault = ''
let activated = false
const result = computed(() => collection.job?.output_ref_json)
const summaryStats = computed(() => {
  const summary = result.value?.summary || {}
  const value = key => result.value ? (summary[key] ?? 0) : '—'
  return [
    { label: '采集行数', value: value('rows') },
    { label: '正样本', value: value('positive_rows') },
    { label: '负样本', value: value('negative_rows') },
    { label: '未标注', value: value('unlabeled_rows') }
  ]
})
const isRunning = computed(() => ['queued', 'running'].includes(collection.job?.status))
const progressText = computed(() => {
  const status = collection.job?.status
  if (!status) return '当前未开始，配置完成后开始收集'
  if (status === 'queued') return '当前正在排队等待执行'
  if (status === 'running') return '当前正在采集提交'
  if (status === 'success') return '当前收集已完成'
  if (status === 'failed') return '当前收集失败，可重试原任务'
  if (status === 'cancelled') return '当前收集已取消'
  return ''
})
function defaultDatasetName() {
  if (source.value === 'public') {
    const urlName = publicDraft.source_url.trim().split('/').filter(Boolean).pop() || ''
    return publicDraft.name.trim() || urlName.replace(/\.[^.]+$/, '') || 'dataset'
  }
  const base = draft.repo_source.trim().split(/[\\/]/).filter(Boolean).pop() || 'collected'
  const range = draft.start_time && draft.end_time ? `${draft.start_time.replace(/-/g, '')}-${draft.end_time.replace(/-/g, '')}` : 'full'
  return `${base}-${range}`
}
function syncDefaultName() {
  const next = defaultDatasetName()
  if (!datasetName.value.trim() || datasetName.value === lastNameDefault) datasetName.value = next
  lastNameDefault = next
}
function message(err) {
  if (err.code === 40100) { auth.value = true; return '登录已失效，请重新登录' }
  return err.code === 50000 ? '服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
function cell(value, column) { return value == null || value === '' ? column === 'is_bug_inducing' ? '未标注' : '' : value }
const collectColumns = computed(() => (collection.preview?.columns || []).map(key => ({ key, label: key, mono: key === 'commit_hash' })))
const collectRows = computed(() => (collection.preview?.preview || []).map(row => Object.fromEntries(
  (collection.preview?.columns || []).map(key => [key, cell(row[key], key)])
)))
const collectFiles = computed(() => (result.value?.outputs || [])
  .filter(item => item.name === `collected_commits_${collection.job?.job_id}.csv`)
  .map(item => ({
    ...item,
    label: '已标注数据集',
    testid: 'collect-download-csv',
    disabled: downloading.value || auth.value
  })))
function configItem(key) { return configuration.items.find(item => item.config_key === key) }
function normalizePath(path) {
  const parts = []
  for (const part of path.replace(/\\/g, '/').split('/')) {
    if (part === '..') parts.pop()
    else if (part && part !== '.') parts.push(part)
  }
  return '/' + parts.join('/')
}
function sourceError(sourceValue) {
  if (sourceValue.includes('://')) {
    let url
    try { url = new URL(sourceValue) } catch { return '仓库地址不可用，请检查后重试' }
    if (!url.hostname || url.username || url.password || url.search || url.hash) return '仓库地址不可用，请检查后重试'
    const policy = configItem('collect.protocol_whitelist')
    if (policy && !policy.value.some(protocol => protocol === url.protocol.slice(0, -1))) return '仓库地址不可用，请检查后重试'
  } else {
    // 允许 POSIX 绝对路径与 Windows 盘符路径；相对路径交由后端拒绝。
    if (!/^(?:[a-zA-Z]:[\\/]|\/)/.test(sourceValue)) return '请输入本地仓库路径或仓库地址'
    const policy = configItem('collect.allow_roots')
    const path = normalizePath(sourceValue)
    if (policy && !policy.value.some(root => {
      root = normalizePath(root)
      return root === '/' || path === root || path.startsWith(root + '/')
    })) return '仓库地址不可用，请检查后重试'
  }
  return ''
}
// 后端没有仓库分支枚举接口；这里只做本地路径/URL 白名单校验，分支由用户手填。
function checkRepo() {
  repoError.value = sourceError(draft.repo_source.trim()) || ''
}
watch(() => draft.repo_source, () => {
  draft.branch = ''
  branches.value = []
  branchError.value = ''
  repoError.value = ''
})
watch(() => publicDraft.source_url, () => {
  publicColumns.value = []
  mappingIssues.value = []
  columnsError.value = ''
})
watch(dateRange, value => {
  const start = value?.[0] || '', end = value?.[1] || ''
  if (start && end && end <= start) {
    dateRange.value = [start, '']
    return
  }
  draft.start_time = start
  draft.end_time = end
})
watch([() => draft.start_time, () => draft.end_time], syncDefaultName)
watch(() => publicDraft.mapping, evaluateMapping, { deep: true })
watch(() => publicDraft.name, syncDefaultName)

function setSource(next) {
  if (source.value === next || busy.value || isRunning.value) return
  source.value = next
  repoError.value = ''
  dateRange.value = []
  draft.start_time = ''
  draft.end_time = ''
  datasetName.value = ''
  lastNameDefault = ''
  const query = { ...route.query }
  if (next === 'public') query.source = 'public'
  else delete query.source
  router.replace({ path: '/collect', query, hash: route.hash })
}
function evaluateMapping() {
  if (!publicColumns.value.length) {
    mappingIssues.value = []
    return
  }
  const lower = publicColumns.value.map(column => column.toLowerCase())
  mappingIssues.value = mappingFields
    .filter(field => field.required && !lower.includes((publicDraft.mapping[field.key] || '').toLowerCase()))
    .map(field => field.label)
}
function autoMapColumns(columns) {
  const lower = columns.map(column => column.toLowerCase())
  for (const [key, candidates] of Object.entries(commonColumns)) {
    const found = candidates.find(name => lower.includes(name))
    publicDraft.mapping[key] = found ? columns[lower.indexOf(found)] : ''
  }
  evaluateMapping()
}
async function loadBranches() {
  if (!draft.repo_source.trim()) return
  branchesLoading.value = true
  branchError.value = ''
  try {
    const data = await getCollectBranches(draft.repo_source.trim())
    branches.value = Array.isArray(data.branches) ? data.branches : []
    draft.branch = data.default_branch && branches.value.includes(data.default_branch)
      ? data.default_branch
      : (branches.value[0] || '')
    if (!branches.value.length) branchError.value = '未找到可用分支，请检查仓库 URL 或权限'
  } catch (err) {
    branches.value = []
    draft.branch = ''
    branchError.value = message(err)
  } finally {
    branchesLoading.value = false
  }
}
async function loadPublicColumns() {
  const sourceUrl = publicDraft.source_url.trim()
  if (!sourceUrl) return
  columnsLoading.value = true
  columnsError.value = ''
  try {
    const data = await getCollectSourceColumns(sourceUrl)
    publicColumns.value = Array.isArray(data.columns) ? data.columns : []
    if (!publicColumns.value.length) columnsError.value = '远端文件没有可用列'
    if (!publicDraft.name.trim()) {
      const urlName = sourceUrl.split('/').filter(Boolean).pop() || ''
      publicDraft.name = urlName.replace(/\.[^.]+$/, '') || 'dataset'
    }
    autoMapColumns(publicColumns.value)
    syncDefaultName()
  } catch (err) {
    publicColumns.value = []
    mappingIssues.value = []
    columnsError.value = message(err)
  } finally {
    columnsLoading.value = false
  }
}

async function startCollect(config, files) {
  busy.value = true
  autoSaveJobId = ''
  saveMessage.value = ''
  try {
    const accepted = await runCollect(config, files)
    if (!accepted?.job_id || !['queued', 'running', 'success'].includes(accepted.status)) throw new Error('收集响应不完整')
    collection.request = { ...config }
    collection.preview = null
    openResultSections.value = []
    collection.job = accepted
    scrollToResults()
    importDraft.name = config.dataset_name
    importDraft.repo_source = config.repo_source || config.source_url || ''
    autoSaveJobId = accepted.job_id
    await refreshJob()
  } catch (err) { error.value = message(err) }
  finally { busy.value = false }
}
async function submit() {
  if (busy.value || auth.value || isRunning.value || !canRun.value) return
  error.value = ''
  if (source.value === 'public') {
    if (!publicReady.value) {
      error.value = '请先读取字段并完成必填列映射'
      return
    }
    const config = {
      source_type: 'public_dataset',
      source_url: publicDraft.source_url.trim(),
      dataset_name: datasetName.value.trim(),
      field_mapping: { ...publicDraft.mapping },
      label_mapping: { positive: publicDraft.label_yes.trim(), negative: publicDraft.label_no.trim() }
    }
    if (publicDraft.license.trim()) config.license = publicDraft.license.trim()
    await startCollect(config, [])
    return
  }
  if (!draft.branch || !branches.value.includes(draft.branch)) {
    error.value = '请先刷新分支并选择可用分支'
    return
  }
  // 只提交后端 collect.validate_config 认可的字段
  const config = {
    repo_source: draft.repo_source.trim(),
    branch: draft.branch,
    dataset_name: datasetName.value.trim()
  }
  if (draft.start_time) config.start_time = draft.start_time
  if (draft.end_time) config.end_time = draft.end_time
  await startCollect(config, [])
}
async function saveAutomatically() {
  const id = collection.job?.job_id
  if (!id || !result.value || saving.value) return
  saving.value = true
  saveMessage.value = ''
  try {
    const response = await resaveCollect(id)
    if (!response?.dataset_id) throw new Error('保存响应不完整')
    saveMessage.value = `已保存到数据集库：${importDraft.name.trim() || defaultDatasetName()}`
  } catch (err) { saveMessage.value = '自动保存未成功：' + message(err) }
  finally { saving.value = false }
}
// 提交预览按页读取全部采集结果，用户可翻页查看完整数据而不是只看前几条。
async function loadPreview(page = 1) {
  const id = collection.job?.job_id
  if (!id) return
  try {
    const data = await getCollectPreview(id, { page, size: previewSize })
    if (collection.job?.job_id !== id) return
    collection.preview = data
    previewPage.value = data.page || page
    previewError.value = ''
    openResultSections.value = (data.preview || []).length ? ['preview'] : []
  } catch (err) { previewError.value = message(err) }
}
async function refreshJob() {
  if (!collection.job?.job_id || jobLoading.value || auth.value) return
  clearTimeout(timer)
  const id = collection.job.job_id, epoch = ++jobEpoch
  jobLoading.value = true
  try {
    const job = await getJob(id)
    if (!mounted || epoch !== jobEpoch || collection.job?.job_id !== id) return
    if (job.job_id !== id || !['queued', 'running', 'success', 'failed', 'cancelled'].includes(job.status)) throw new Error('任务响应不完整')
    collection.job = job
    if (job.status === 'success' && !collection.preview) await loadPreview(1)
    if (job.status === 'success' && id === autoSaveJobId) {
      autoSaveJobId = ''
      await saveAutomatically()
    }
  } catch (err) { if (epoch === jobEpoch && mounted) error.value = message(err) }
  finally {
    jobLoading.value = false
    if (mounted && epoch === jobEpoch && ['queued', 'running'].includes(collection.job?.status)) timer = setTimeout(refreshJob, 1500)
  }
}
async function retry() {
  try {
    const id = collection.job.job_id
    await retryJob(id)
    // 重试响应字段不完整，统一以任务详情为准
    collection.job = await getJob(id)
    collection.preview = null
    openResultSections.value = []
    autoSaveJobId = id
    saveMessage.value = ''
    await refreshJob()
  } catch (err) { error.value = message(err) }
}
async function cancel() {
  try {
    const id = collection.job.job_id
    await cancelJob(id)
    jobEpoch++
    clearTimeout(timer)
    collection.job = await getJob(id)
    autoSaveJobId = ''
  } catch (err) { error.value = message(err) }
}
async function download(name) {
  downloading.value = true
  try {
    saveBlob(await fetchCollectOutput(collection.job.job_id, name), name)
  } catch (err) { error.value = message(err) }
  finally { downloading.value = false }
}
onActivated(async () => {
  mounted = true; jobEpoch++
  // 二次进入只续接任务进度，保留本页已填写的来源与命名。
  if (activated) { await refreshJob(); return }
  activated = true
  if (route.query.source === 'public') {
    const query = { ...route.query }
    delete query.source
    router.replace({ path: '/collect', query, hash: route.hash })
  }
  if (!collection.job) {
    try { const data = await getJobs({ kind: 'collect', page: 1, size: 1 }); collection.job = data.items?.[0] || null }
    catch (err) { error.value = message(err) }
  }
  if (collection.request) {
    importDraft.name = collection.request.dataset_name || ''
    importDraft.repo_source = collection.request.repo_source || collection.request.source_url || ''
    if (!datasetName.value) datasetName.value = importDraft.name
    lastNameDefault = datasetName.value
  }
  syncDefaultName()
  await refreshJob()
})
onDeactivated(() => { mounted = false; clearTimeout(timer) })
</script>

<style scoped>
.collect-tool { min-width: 0; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--ui-space-4) var(--ui-space-5); }
.field-line { display: flex; align-items: center; gap: 8px; min-width: 0; }
.field-line :deep(.el-input),
.field-line :deep(.el-select) { flex: 1; min-width: 0; }
.field-hint { font-size: var(--ui-font-hint); color: var(--ui-text-muted); white-space: nowrap; }
.field-required { margin-left: 2px; color: var(--el-color-danger); }
.field :deep(.el-date-editor) { width: 100%; }
.field-invalid :deep(.el-select__wrapper),
.field-invalid :deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--el-color-danger) inset;
}
@media (max-width: 768px) {
  .fields { grid-template-columns: minmax(0, 1fr); }
}
.pagination { margin-top: 16px; justify-content: flex-end; }
</style>
