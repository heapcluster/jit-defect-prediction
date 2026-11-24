<template>
  <section class="storage">
    <el-tabs
      v-model="activeSection"
      data-testid="storage-tabs"
    >
      <el-tab-pane
        label="数据导入导出"
        name="data"
      >
        <p class="hint">
          导入用于可选的展示与资产登记；各文件模块可独立运行，不要求数据库已有数据。本页不执行采集、训练或预测。
        </p>
        <section
          class="panel"
          aria-labelledby="import-heading"
          :aria-busy="importState.loading"
        >
          <div class="section-heading">
            <h2 id="import-heading">
              文件导入
            </h2>
            <span>自动识别目标表 · 按自然键幂等 upsert</span>
          </div>
          <p
            id="file-help"
            class="hint"
          >
            选择多个 CSV / XLSX / ZIP / PNG 及同名 .manifest.json；文件格式、大小、checksum 和目标表由后端校验。
          </p>
          <p class="hint">
            commits / cleaned 必须附带经校验的 manifest.config.feature_version；CSV 本身没有此列，缺失时后端返回 40001，不自动补版本。
          </p>
          <el-alert
            v-if="importState.error"
            :title="importState.error"
            type="error"
            :closable="false"
            show-icon
            class="notice"
          />
          <el-form
            label-position="top"
            :disabled="importState.loading || importState.auth"
            @submit.prevent="submitImport"
          >
            <el-form-item
              label="选择交换文件及伴随 manifest"
              for="storage-files"
            >
              <input
                id="storage-files"
                data-testid="import-files"
                type="file"
                multiple
                accept=".csv,.xlsx,.zip,.png,.manifest.json"
                aria-describedby="file-help"
                :disabled="importState.loading || importState.auth"
                @change="appendFiles"
              >
            </el-form-item>
            <ul
              v-if="files.length"
              data-testid="selected-files"
              class="file-list"
            >
              <li
                v-for="(file, index) in files"
                :key="`${file.name}-${index}`"
              >
                <span>{{ file.name }} · {{ file.size }} bytes · 等待后端校验</span>
                <el-button
                  size="small"
                  :aria-label="`移除 ${file.name}`"
                  @click="files.splice(index, 1)"
                >
                  移除
                </el-button>
              </li>
            </ul>
            <div class="field-grid">
              <el-form-item
                label="关联已有数据集（可选，仅 ready）"
                data-testid="import-dataset"
                for="import-dataset"
              >
                <el-select
                  id="import-dataset"
                  v-model="importDraft.dataset_id"
                  aria-label="关联已有数据集"
                  clearable
                  :disabled="datasetsState.loading || datasetsState.auth || !!datasetsState.error || creatingDataset"
                >
                  <el-option
                    label="不关联数据集"
                    value=""
                  />
                  <el-option
                    v-for="item in readyDatasets"
                    :key="item.dataset_id"
                    :label="`${item.name} · ${item.dataset_id}`"
                    :value="item.dataset_id"
                  />
                </el-select>
              </el-form-item>
              <div class="hint field-note">
                可不关联数据集直接导入。已有数据集与新建配置不能同时提交；列表仅显示当前页的真实登记版本。
              </div>
              <el-form-item
                label="新数据集名称（可选）"
                data-testid="dataset-name"
                for="dataset-name"
              >
                <el-input
                  id="dataset-name"
                  v-model="importDraft.name"
                  aria-label="新数据集名称"
                  :disabled="!!importDraft.dataset_id"
                />
              </el-form-item>
              <el-form-item
                label="新数据集来源仓库（与名称一起填写）"
                data-testid="repo-source"
                for="repo-source"
              >
                <el-input
                  id="repo-source"
                  v-model="importDraft.repo_source"
                  aria-label="新数据集来源仓库"
                  :disabled="!!importDraft.dataset_id"
                />
              </el-form-item>
              <el-form-item
                label="模型包登记状态（可选）"
                for="artifact-status"
              >
                <el-select
                  id="artifact-status"
                  v-model="importDraft.model_artifact_status"
                  aria-label="模型包登记状态"
                  clearable
                >
                  <el-option
                    label="由后端使用默认值"
                    value=""
                  />
                  <el-option
                    label="可用（available）"
                    value="available"
                  />
                  <el-option
                    label="退役（retired）"
                    value="retired"
                  />
                </el-select>
              </el-form-item>
              <el-form-item
                label="登记 evaluate 图（可选）"
                for="register-figures"
              >
                <el-select
                  id="register-figures"
                  v-model="importDraft.register_figures"
                  aria-label="登记 evaluate 图"
                >
                  <el-option
                    label="由后端使用默认值"
                    value=""
                  />
                  <el-option
                    label="登记"
                    :value="true"
                  />
                  <el-option
                    label="不登记"
                    :value="false"
                  />
                </el-select>
              </el-form-item>
            </div>
            <div class="actions">
              <el-button
                data-testid="submit-import"
                type="primary"
                native-type="submit"
                :loading="importState.loading"
                :disabled="!files.length || importState.loading || importState.auth"
              >
                {{ importState.error && !importState.auth ? '重试导入' : '导入所选文件' }}
              </el-button>
              <span
                role="status"
                aria-live="polite"
                class="hint"
              >{{ importState.loading ? '正在等待后端同步校验及导入结果…' : importStatus }}</span>
            </div>
          </el-form>
          <template v-if="importItems.length">
            <p class="hint">
              以下为最近完成请求的逐文件结果；存在 rejected 时不代表全部成功。每个文件的多表写入由后端事务保证。
            </p>
            <div class="table-scroll">
              <el-table
                data-testid="import-results"
                :data="importItems"
                border
                size="small"
              >
                <el-table-column
                  prop="name"
                  label="文件"
                  min-width="170"
                />
                <el-table-column
                  prop="schema"
                  label="识别 schema"
                  min-width="120"
                />
                <el-table-column
                  label="目标表"
                  min-width="180"
                >
                  <template #default="{ row }">
                    {{ row.target_tables.join(', ') }}
                  </template>
                </el-table-column>
                <el-table-column
                  label="状态"
                  min-width="100"
                >
                  <template #default="{ row }">
                    <el-tag
                      :type="isRejected(row) ? 'danger' : 'info'"
                      size="small"
                    >
                      {{ row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column
                  v-for="count in countFields"
                  :key="count"
                  :prop="count"
                  :label="count"
                  width="100"
                />
                <el-table-column
                  label="原因"
                  min-width="220"
                >
                  <template #default="{ row }">
                    {{ row.errors.join('；') }}
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </section>

        <section
          class="panel"
          aria-labelledby="export-heading"
          :aria-busy="exportState.loading"
        >
          <div class="section-heading">
            <h2 id="export-heading">
              按表导出
            </h2>
            <span>只读数据库原始表 · 文件由服务端生成</span>
          </div>
          <p class="hint">
            提交表导出不包含 14 维特征交换列，不能冒充 commits / cleaned 模块输入。预览产物不是完整文件；完整下载会重新生成不带 limit 的批次。
          </p>
          <el-alert
            v-if="tablesState.error"
            :title="tablesState.error"
            type="error"
            :closable="false"
            class="notice"
          >
            <el-button
              v-if="!tablesState.auth"
              data-testid="retry-tables"
              :disabled="tablesState.loading"
              @click="loadTables"
            >
              重试读取表选项
            </el-button>
          </el-alert>
          <el-alert
            v-if="exportState.error"
            :title="exportState.error"
            type="error"
            :closable="false"
            class="notice"
          >
            <el-button
              v-if="!exportState.auth"
              data-testid="retry-export"
              :disabled="exportState.loading"
              @click="retryExport"
            >
              重试上次操作
            </el-button>
          </el-alert>
          <el-form
            label-position="top"
            :disabled="exportState.loading || exportState.auth"
            @submit.prevent="runExport('csv', true)"
          >
            <div class="field-grid">
              <el-form-item
                label="选择数据库表"
                for="export-table"
                data-testid="export-table"
              >
                <el-select
                  id="export-table"
                  v-model="exportTable"
                  aria-label="选择数据库表"
                  :loading="tablesState.loading"
                  :disabled="tablesState.loading || tablesState.auth || !!tablesState.error || !tableItems.length"
                >
                  <el-option
                    v-for="item in tableItems"
                    :key="item.name"
                    :label="item.name"
                    :value="item.name"
                  />
                </el-select>
              </el-form-item>
              <el-form-item
                v-for="filter in allowedFilters"
                :key="filter"
                :label="filterLabels[filter]"
                :for="`export-${filter}`"
                :data-testid="`filter-${filter}`"
              >
                <el-select
                  v-if="filter === 'dataset_id'"
                  :id="`export-${filter}`"
                  v-model="exportFilters[filter]"
                  :aria-label="filterLabels[filter]"
                  clearable
                  :disabled="datasetsState.loading || datasetsState.auth || !!datasetsState.error"
                >
                  <el-option
                    label="全部数据集"
                    value=""
                  />
                  <el-option
                    v-for="item in datasetItems"
                    :key="item.dataset_id"
                    :label="`${item.name} · ${item.dataset_id}`"
                    :value="item.dataset_id"
                  />
                </el-select>
                <el-input
                  v-else
                  :id="`export-${filter}`"
                  v-model="exportFilters[filter]"
                  :aria-label="filterLabels[filter]"
                  :placeholder="filter.includes('time') ? 'ISO 时间，例如 2026-11-01T00:00:00Z' : '填写已登记的模型名称，留空为全部'"
                />
              </el-form-item>
            </div>
            <div class="actions">
              <el-button
                data-testid="preview-export"
                native-type="submit"
                :disabled="!canExport"
                :loading="exportState.loading"
              >
                预览前 20 行
              </el-button>
              <el-button
                data-testid="download-csv"
                type="primary"
                :disabled="!canExport"
                @click="runExport('csv', false)"
              >
                下载完整 CSV
              </el-button>
              <el-button
                data-testid="download-xlsx"
                :disabled="!canExport"
                @click="runExport('xlsx', false)"
              >
                下载完整 XLSX
              </el-button>
              <el-button
                data-testid="download-manifest"
                :disabled="!exportBatch || exportState.loading || exportState.auth"
                @click="downloadManifest"
              >
                下载当前批次 manifest
              </el-button>
            </div>
          </el-form>
          <p
            v-if="exportState.loading"
            role="status"
            class="hint"
          >
            正在等待后端导出或下载结果…
          </p>
          <template v-if="exportBatch">
            <p
              role="status"
              class="hint"
            >
              {{ batchPreview ? '预览批次（最多 20 行，产物不是完整文件）' : '完整导出批次' }} · {{ exportBatch.table }} · {{ exportBatch.format }} · 批次 {{ exportBatch.job_id }} · 本批次 {{ exportBatch.row_count }} 行<span v-if="exportBatch.total != null"> · 查询总数 {{ exportBatch.total }} 行</span>
            </p>
            <p
              v-if="exportState.error"
              class="hint"
            >
              上次完成的批次仍保留在下方，不能视为本次失败操作的结果。
            </p>
            <ul class="file-list">
              <li
                v-for="output in exportBatch.outputs"
                :key="output.name"
              >
                <span>{{ output.name }} · {{ output.size_bytes }} bytes<br>SHA-256：{{ output.sha256 }}</span>
              </li>
            </ul>
            <p
              v-if="!exportBatch.preview.length"
              class="hint"
            >
              当前查询没有可预览记录，未生成任何虚构数据。
            </p>
            <div
              v-else
              class="table-scroll"
              data-testid="export-preview"
              tabindex="0"
              aria-label="导出结果预览，可横向滚动"
            >
              <table class="result-table">
                <thead>
                  <tr>
                    <th
                      v-for="column in exportBatch.columns"
                      :key="column"
                      scope="col"
                    >
                      {{ column }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(row, index) in exportBatch.preview"
                    :key="index"
                  >
                    <td
                      v-for="column in exportBatch.columns"
                      :key="column"
                    >
                      {{ displayCell(row[column], column) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </section>

        <section
          class="panel"
          aria-labelledby="datasets-heading"
          :aria-busy="datasetsState.loading"
        >
          <div class="section-heading">
            <h2 id="datasets-heading">
              数据集版本列表
            </h2>
            <el-button
              :disabled="datasetsState.loading || datasetsState.auth"
              @click="loadDatasets(datasetPage)"
            >
              刷新列表
            </el-button>
          </div>
          <el-alert
            v-if="datasetsState.error"
            :title="datasetsState.error"
            type="error"
            :closable="false"
            class="notice"
          >
            <el-button
              v-if="!datasetsState.auth"
              data-testid="retry-datasets"
              :disabled="datasetsState.loading"
              @click="loadDatasets(datasetPage)"
            >
              重试读取数据集
            </el-button>
          </el-alert>
          <p
            v-if="datasetsState.loading"
            role="status"
            class="hint"
          >
            正在读取数据集…
          </p>
          <p
            v-else-if="datasetsInitialized && !datasetItems.length && !datasetsState.error"
            class="hint"
          >
            暂无已导入数据集，可从上方上传 commits.csv 及同名 manifest；不导入也可独立运行文件模块。
          </p>
          <div class="table-scroll">
            <el-table
              data-testid="datasets"
              :data="datasetItems"
              border
              size="small"
            >
              <el-table-column
                prop="name"
                label="名称"
                min-width="140"
              />
              <el-table-column
                prop="dataset_id"
                label="dataset_id"
                min-width="180"
              />
              <el-table-column
                prop="repo_source"
                label="来源仓库"
                min-width="200"
              />
              <el-table-column
                prop="branch"
                label="分支"
                min-width="100"
              />
              <el-table-column
                prop="head_hash"
                label="HEAD"
                min-width="150"
              />
              <el-table-column
                prop="sample_count"
                label="样本数"
                width="85"
              />
              <el-table-column
                prop="pos_count"
                label="正样本"
                width="85"
              />
              <el-table-column
                prop="neg_count"
                label="负样本"
                width="85"
              />
              <el-table-column
                label="未打标"
                width="85"
              >
                <template #default="{ row }">
                  {{ Math.max(row.sample_count - row.pos_count - row.neg_count, 0) }}
                </template>
              </el-table-column>
              <el-table-column
                prop="status"
                label="状态"
                min-width="100"
              />
              <el-table-column
                prop="created_at"
                label="创建时间"
                min-width="200"
              />
              <el-table-column
                label="操作"
                min-width="250"
              >
                <template #default="{ row }">
                  <el-button
                    data-testid="view-members"
                    size="small"
                    :disabled="datasetsState.auth"
                    @click="openMembers(row)"
                  >
                    查看成员
                  </el-button>
                  <el-button
                    data-testid="export-dataset"
                    size="small"
                    :disabled="!canExportDataset"
                    @click="runExport('csv', false, row.dataset_id)"
                  >
                    提交表导出 CSV
                  </el-button>
                </template>
              </el-table-column>
              <template #empty>
                {{ datasetsState.error ? '读取失败，未替换已有记录' : datasetsState.loading ? '正在读取' : '没有已登记的数据集' }}
              </template>
            </el-table>
          </div>
          <div class="table-scroll pagination">
            <el-pagination
              data-testid="dataset-pagination"
              :current-page="datasetPage"
              :page-size="20"
              :total="datasetTotal"
              :disabled="datasetsState.loading || datasetsState.auth"
              layout="total, prev, pager, next"
              @current-change="loadDatasets"
            />
          </div>
        </section>
      </el-tab-pane>
      <el-tab-pane
        label="用户配置"
        name="config"
        lazy
      >
        <Settings v-if="configOpened" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog
      v-model="membersVisible"
      :title="`数据集成员：${memberDataset?.name || ''}`"
      width="min(960px, calc(100vw - 32px))"
      append-to-body
    >
      <p class="hint">
        只读提交、标签与时间序划分；仅展示响应中实际返回的可选特征。
      </p>
      <el-alert
        v-if="membersState.error"
        :title="membersState.error"
        type="error"
        :closable="false"
        class="notice"
      >
        <el-button
          v-if="!membersState.auth"
          :disabled="membersState.loading"
          @click="loadMembers(memberPage)"
        >
          重试读取成员
        </el-button>
      </el-alert>
      <p
        v-if="membersState.loading"
        role="status"
        class="hint"
      >
        正在读取成员…
      </p>
      <div
        class="table-scroll"
        tabindex="0"
        aria-label="数据集成员，可横向滚动"
      >
        <table class="result-table">
          <thead>
            <tr>
              <th scope="col">
                commit_hash
              </th>
              <th scope="col">
                committed_at
              </th>
              <th scope="col">
                message
              </th>
              <th scope="col">
                label
              </th>
              <th scope="col">
                is_test
              </th>
              <th scope="col">
                可选特征（实际返回值）
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, index) in memberItems"
              :key="index"
            >
              <td>{{ row.commit_hash }}</td>
              <td>{{ row.committed_at }}</td>
              <td>{{ row.message }}</td>
              <td>{{ displayCell(Object.hasOwn(row, 'label') ? row.label : row.is_bug_inducing, 'label') }}</td>
              <td>{{ displayCell(row.is_test, 'is_test') }}</td>
              <td>{{ memberFeatures(row) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p
        v-if="!membersState.loading && !membersState.error && !memberItems.length"
        class="hint"
      >
        当前数据集暂无成员。
      </p>
      <div class="table-scroll pagination">
        <el-pagination
          data-testid="member-pagination"
          :current-page="memberPage"
          :page-size="20"
          :total="memberTotal"
          :disabled="membersState.loading || membersState.auth"
          layout="total, prev, pager, next"
          @current-change="loadMembers"
        />
      </div>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { exportStorageTable, fetchStorageOutput, getDatasetCommits, getDatasets, getStorageTables, importStorageFiles } from '../api'
import Settings from './Settings.vue'

defineOptions({ name: 'StorageWorkspace' })
const route = useRoute()
const router = useRouter()
const activeSection = computed({
  get: () => route.query.section === 'config' ? 'config' : 'data',
  set: value => {
    const query = { ...route.query }
    if (value === 'config') query.section = 'config'
    else delete query.section
    router.replace({ path: '/storage', query, hash: route.hash })
  }
})
const configOpened = ref(false)
watch(activeSection, value => { if (value === 'config') configOpened.value = true }, { immediate: true })
const state = () => reactive({ loading: false, error: '', auth: false })
const tablesState = state()
const importState = state()
const exportState = state()
const datasetsState = state()
const membersState = state()
const tableItems = ref([])
const files = ref([])
const importDraft = reactive({ dataset_id: '', name: '', repo_source: '', model_artifact_status: '', register_figures: '' })
const creatingDataset = computed(() => !!(importDraft.name.trim() || importDraft.repo_source.trim()))
const importItems = ref([])
const importStatus = ref('')
const countFields = ['inserted', 'updated', 'unchanged', 'rejected']
const isRejected = item => item.rejected > 0 || /reject|fail|error/i.test(item.status)
const datasetItems = ref([])
const datasetsInitialized = ref(false)
const datasetPage = ref(1)
const datasetTotal = ref(0)
const readyDatasets = computed(() => datasetItems.value.filter(item => item.status === 'ready'))
const exportTable = ref('')
const exportFilters = reactive({})
const filterLabels = {
  dataset_id: '筛选数据集（留空为全部）', model_name: '筛选已登记模型名称',
  start_time: '起始时间（可选，ISO）', end_time: '结束时间（可选，ISO）'
}
const selectedTable = computed(() => tableItems.value.find(item => item.name === exportTable.value))
const allowedFilters = computed(() => (selectedTable.value?.filters || []).filter(filter => Object.hasOwn(filterLabels, filter)))
const metadataAvailable = computed(() => !tablesState.loading && !tablesState.auth && !tablesState.error)
const canExport = computed(() => metadataAvailable.value && !!selectedTable.value && !exportState.loading && !exportState.auth)
const canExportDataset = computed(() => metadataAvailable.value && tableItems.value.some(item => item.name === 'commit' && item.filters.includes('dataset_id')) && !exportState.loading && !exportState.auth && !datasetsState.auth)
const exportBatch = ref(null)
const batchPreview = ref(false)
let lastExportAction = null
const membersVisible = ref(false)
const memberDataset = ref(null)
const memberItems = ref([])
const memberPage = ref(1)
const memberTotal = ref(0)
let memberRequest = 0

const isObject = value => value !== null && typeof value === 'object' && !Array.isArray(value)
const countValid = value => Number.isInteger(value) && value >= 0
const stringArray = value => Array.isArray(value) && value.every(item => typeof item === 'string')
function showError(target, error, fallback) {
  if (error.code === 40100) {
    target.auth = true
    target.error = '鉴权失败，请检查部署环境中的 API Key；本页不提供密钥编辑。'
  } else if (error.code === 50000 || error.response?.status >= 500) {
    target.error = '服务异常，请稍后重试'
  } else if (error.code === 40400) {
    target.error = '数据集或导出文件不存在，请刷新列表或重新导出'
  } else {
    target.error = (error.code === 40001 ? error.detail : '') || error.message || fallback
  }
}
function validPage(data, itemValidator) {
  return isObject(data) && countValid(data.total) && Number.isInteger(data.page) && data.page >= 1 &&
    Number.isInteger(data.size) && data.size > 0 && Array.isArray(data.items) && data.items.every(itemValidator)
}
function validTable(item) {
  return isObject(item) && typeof item.name === 'string' && item.name.length &&
    stringArray(item.columns) && stringArray(item.filters)
}
function validDataset(item) {
  return isObject(item) && typeof item.dataset_id === 'string' && item.dataset_id.length &&
    typeof item.name === 'string' && typeof item.repo_source === 'string' && typeof item.status === 'string' &&
    ['sample_count', 'pos_count', 'neg_count'].every(key => countValid(item[key]))
}
function validImportItem(item) {
  return isObject(item) && typeof item.name === 'string' && typeof item.status === 'string' &&
    stringArray(item.target_tables) && stringArray(item.errors) && countFields.every(key => countValid(item[key]))
}
function validOutput(output) {
  return isObject(output) && typeof output.name === 'string' && output.name.length && !/[\\/]/.test(output.name) &&
    typeof output.sha256 === 'string' && /^[a-f0-9]{64}$/i.test(output.sha256) && countValid(output.size_bytes)
}
async function loadTables() {
  if (tablesState.loading || tablesState.auth) return
  tablesState.loading = true
  tablesState.error = ''
  try {
    const data = await getStorageTables()
    if (!Array.isArray(data?.items) || !data.items.every(validTable)) throw new Error('表元数据响应不完整，请重试')
    tableItems.value = data.items
    if (!data.items.some(item => item.name === exportTable.value)) exportTable.value = data.items[0]?.name || ''
  } catch (error) {
    showError(tablesState, error, '表选项读取失败')
  } finally {
    tablesState.loading = false
  }
}
async function loadDatasets(page = datasetPage.value) {
  if (datasetsState.loading || datasetsState.auth) return
  datasetsState.loading = true
  datasetsState.error = ''
  try {
    const data = await getDatasets({ page, size: 20 })
    if (!validPage(data, validDataset)) throw new Error('数据集响应不完整，请重试')
    datasetItems.value = data.items
    datasetTotal.value = data.total
    datasetPage.value = data.page
    datasetsInitialized.value = true
  } catch (error) {
    showError(datasetsState, error, '数据集读取失败')
  } finally {
    datasetsState.loading = false
  }
}
function appendFiles(event) {
  if (importState.loading || importState.auth) return
  for (const file of Array.from(event.target.files || [])) files.value.push(file)
  // File objects remain selected in state; reset the picker to allow reselecting a file.
  event.target.value = ''
}
async function submitImport() {
  if (importState.loading || importState.auth || !files.value.length) return
  importState.error = ''
  importStatus.value = ''
  const config = {}
  if (importDraft.dataset_id) {
    if (creatingDataset.value) { importState.error = '不能同时关联已有数据集和新建数据集'; return }
    config.dataset_id = importDraft.dataset_id
  } else if (creatingDataset.value) {
    const name = importDraft.name.trim()
    const repo_source = importDraft.repo_source.trim()
    if (!name || !repo_source) { importState.error = '新建数据集需要同时填写名称和来源仓库'; return }
    config.create_dataset = { name, repo_source }
  }
  if (importDraft.model_artifact_status) config.model_artifact_status = importDraft.model_artifact_status
  if (typeof importDraft.register_figures === 'boolean') config.register_figures = importDraft.register_figures
  importState.loading = true
  try {
    const data = await importStorageFiles(files.value, config)
    if (!isObject(data?.summary) || !Array.isArray(data?.items) || !data.items.length || !data.items.every(validImportItem)) {
      throw new Error('导入响应不完整，请重试；所选文件与草稿已保留')
    }
    importItems.value = data.items
    importStatus.value = data.items.some(isRejected)
      ? '导入请求已完成，存在拒绝项，请逐文件查看原因' : '导入请求已完成，请查看逐文件计数'
    await loadDatasets(datasetPage.value)
  } catch (error) {
    showError(importState, error, '导入失败，文件与草稿已保留')
  } finally {
    importState.loading = false
  }
}
function exportParams(format, preview, datasetId) {
  if (datasetId !== undefined) return { table: 'commit', format, dataset_id: datasetId }
  const params = { table: exportTable.value, format }
  for (const key of allowedFilters.value) {
    const value = exportFilters[key]
    if (typeof value === 'string' && value.trim()) params[key] = value.trim()
  }
  if (preview) params.limit = 20
  return params
}
function validateBatch(data, params) {
  const valid = isObject(data) && typeof data.job_id === 'string' && data.job_id &&
    data.table === params.table && data.format === params.format && stringArray(data.columns) &&
    Array.isArray(data.preview) && data.preview.every(isObject) && countValid(data.row_count) &&
    (data.total == null || countValid(data.total)) && typeof data.manifest_name === 'string' &&
    Array.isArray(data.outputs) && data.outputs.every(validOutput) &&
    data.outputs.some(output => output.name === data.manifest_name) &&
    data.outputs.some(output => output.name.endsWith(`.${params.format}`))
  if (!valid) throw new Error('导出响应不完整，请重试；未下载任何伪造文件')
}
async function downloadFile(batch, name) {
  const blob = await fetchStorageOutput(batch.job_id, name)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = name
  document.body.appendChild(link)
  try {
    link.click()
  } finally {
    link.remove()
    URL.revokeObjectURL(url)
  }
}
async function executeExport(action) {
  if (exportState.loading || exportState.auth) return
  lastExportAction = action
  exportState.loading = true
  exportState.error = ''
  try {
    if (action.manifestBatch) {
      await downloadFile(action.manifestBatch, action.manifestBatch.manifest_name)
    } else {
      const data = await exportStorageTable(action.params)
      validateBatch(data, action.params)
      exportBatch.value = data
      batchPreview.value = action.preview
      if (!action.preview) await downloadFile(data, data.outputs.find(output => output.name.endsWith(`.${action.params.format}`)).name)
    }
  } catch (error) {
    showError(exportState, error, '导出失败，请重试')
  } finally {
    exportState.loading = false
  }
}
function runExport(format, preview, datasetId) {
  if (datasetId !== undefined ? !canExportDataset.value : !canExport.value) return
  return executeExport({ params: exportParams(format, preview, datasetId), preview })
}
function downloadManifest() {
  if (!exportBatch.value) return
  return executeExport({ manifestBatch: exportBatch.value })
}
function retryExport() {
  if (lastExportAction) return executeExport(lastExportAction)
}
function displayCell(value, column) {
  if (value == null) return ['label', 'is_bug_inducing'].includes(column) ? '未打标' : ''
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}
const featureKeys = ['ns', 'nd', 'nf', 'entropy', 'la', 'ld', 'lt', 'fix', 'ndev', 'age', 'nuc', 'exp', 'rexp', 'sexp']
function memberFeatures(row) {
  if (isObject(row.features)) return JSON.stringify(row.features)
  const features = Object.fromEntries(featureKeys.filter(key => Object.hasOwn(row, key)).map(key => [key, row[key]]))
  return Object.keys(features).length ? JSON.stringify(features) : ''
}
function openMembers(dataset) {
  memberRequest++
  memberDataset.value = dataset
  memberItems.value = []
  memberPage.value = 1
  memberTotal.value = 0
  membersState.error = ''
  membersState.loading = false
  membersVisible.value = true
  return loadMembers(1)
}
async function loadMembers(page = 1) {
  if (!memberDataset.value || membersState.loading || membersState.auth) return
  const requestId = ++memberRequest
  const id = memberDataset.value.dataset_id
  membersState.loading = true
  membersState.error = ''
  try {
    const data = await getDatasetCommits(id, { page, size: 20, with_features: 1 })
    if (requestId !== memberRequest) return
    if (!validPage(data, item => isObject(item) && typeof item.commit_hash === 'string')) throw new Error('成员响应不完整，请重试')
    memberItems.value = data.items
    memberTotal.value = data.total
    memberPage.value = data.page
  } catch (error) {
    if (requestId === memberRequest) showError(membersState, error, '成员读取失败')
  } finally {
    if (requestId === memberRequest) membersState.loading = false
  }
}
onMounted(() => { loadTables(); loadDatasets(1) })
</script>

<style scoped>
.storage { max-width: 1120px; min-width: 0; margin: 0 auto; }
.panel { min-width: 0; margin: 12px 0 20px; padding: 16px; border: 1px solid var(--el-border-color-lighter); border-radius: var(--el-border-radius-base); }
.section-heading { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 16px; }
.section-heading h2 { margin: 0; font-size: 16px; font-weight: 600; }
.section-heading span, .hint { color: var(--el-text-color-secondary); font-size: 13px; line-height: 1.65; overflow-wrap: anywhere; }
.notice { margin: 12px 0; overflow-wrap: anywhere; }
.field-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 16px; }
.field-note { align-self: center; margin-bottom: 18px; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 8px 0; }
.actions :deep(.el-button + .el-button) { margin-left: 0; }
.file-list { list-style: none; padding: 0; margin: 12px 0; }
.file-list li { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 8px 0; font-size: 13px; }
.file-list span { min-width: 0; overflow-wrap: anywhere; }
input[type="file"] { max-width: 100%; min-width: 0; font: inherit; }
.table-scroll { width: 100%; min-width: 0; max-width: 100%; overflow-x: auto; }
.result-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.result-table th, .result-table td { padding: 8px 12px; text-align: left; vertical-align: top; border: 1px solid var(--el-border-color-lighter); min-width: 100px; max-width: 340px; overflow-wrap: anywhere; }
.result-table th { background: var(--el-fill-color-light); font-weight: 600; }
.pagination { margin-top: 12px; }
:deep(.el-select), :deep(.el-input) { width: 100%; min-width: 0; }
:deep(.el-form-item), :deep(.el-form-item__content), :deep(.el-tabs__content), :deep(.el-tab-pane), :deep(.el-alert__content) { min-width: 0; }
@media (max-width: 640px) {
  .panel { padding: 12px; }
  .field-grid { grid-template-columns: minmax(0, 1fr); }
  .field-note { margin-top: -8px; }
}
</style>
