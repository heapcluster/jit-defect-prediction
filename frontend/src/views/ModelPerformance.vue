<template>
  <div class="panel config-panel content-page">
    <div class="section-heading">
      <h2>模型性能</h2>
    </div>
    <!-- 模型选择区：架构 → 模型级联 + 查看抽屉 -->
    <FilterBar>
      <span class="filter-label">模型</span>
      <LineModelCascade
        v-model:line="selectedLine"
        v-model:model="selectedModel"
        :lines="lines"
        model-placeholder="选择模型"
      />
      <template #actions>
        <el-button
          type="primary"
          :disabled="!selectedModel"
          @click="openDrawer"
        >
          查看
        </el-button>
      </template>
    </FilterBar>

    <!-- 查询栏：搜索 + 时间范围（表格按所选模型与 with_features=1 查询） -->
    <FilterBar>
      <span class="filter-label">搜索</span>
      <el-input
        v-model="filters.q"
        placeholder="哈希/作者/提交信息"
        clearable
        maxlength="64"
        style="width: 200px"
        @keyup.enter="load(1)"
      />
      <el-date-picker
        v-model="timeRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始"
        end-placeholder="结束"
        style="width: 240px"
      />
      <template #actions>
        <el-button
          type="primary"
          @click="load(1)"
        >
          查询
        </el-button>
        <el-button @click="reset">
          重置
        </el-button>
      </template>
    </FilterBar>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="mb"
    >
      <el-button
        v-if="retryable"
        size="small"
        text
        @click="load(filters.page)"
      >
        重试
      </el-button>
    </el-alert>

    <el-table
      v-loading="loading"
      :data="items"
      row-key="commit_hash"
      class="mp-table"
    >
      <el-table-column
        label="提交"
        width="110"
      >
        <template #default="{ row }">
          <el-tooltip
            :content="row.commit_hash"
            placement="top"
          >
            <span class="mono">{{ row.commit_hash.slice(0, 8) }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column
        prop="author_name"
        label="作者"
        width="130"
        show-overflow-tooltip
      />
      <el-table-column
        label="时间"
        width="170"
      >
        <template #default="{ row }">
          {{ formatTime(row.committed_at) }}
        </template>
      </el-table-column>
      <el-table-column
        label="提交信息"
        prop="message"
        show-overflow-tooltip
      />
      <el-table-column
        label="特征详情"
        width="110"
      >
        <template #default="{ row }">
          <el-popover
            placement="left"
            :width="360"
            trigger="hover"
          >
            <template #reference>
              <el-button
                size="small"
                text
                type="primary"
              >
                预览
              </el-button>
            </template>
            <div
              v-for="group in featureGroups"
              :key="group.title"
              class="feat-group"
            >
              <h3>{{ group.title }}</h3>
              <div class="feat-list">
                <span
                  v-for="f in group.fields"
                  :key="f"
                  class="feat-item"
                >
                  {{ featureLabel(f) }}：{{ featureValue(row.features?.[f]) }}
                </span>
              </div>
            </div>
          </el-popover>
        </template>
      </el-table-column>
      <el-table-column
        label="是否为缺陷"
        width="110"
      >
        <template #default="{ row }">
          <el-tag
            v-if="row.is_bug_inducing === 1"
            type="danger"
            size="small"
          >
            是
          </el-tag>
          <el-tag
            v-else-if="row.is_bug_inducing === 0"
            type="success"
            size="small"
          >
            否
          </el-tag>
          <el-tag
            v-else
            type="info"
            size="small"
          >
            未标注
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        label="缺陷引入概率"
        width="140"
      >
        <template #default="{ row }">
          <span
            class="mono"
            :style="{ color: riskColor(row.risk_score) }"
          >
            {{ (row.risk_score * 100).toFixed(1) }}%
          </span>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="total > 0"
      class="pager"
      layout="prev, pager, next, total"
      :total="total"
      :page-size="filters.size"
      :current-page="filters.page"
      @current-change="load"
    />

    <!-- 查看抽屉：性能图集 + 指标（全屏） -->
    <el-drawer
      v-model="drawerVisible"
      :title="drawerTitle"
      size="100%"
    >
      <div
        v-loading="drawerLoading"
        class="drawer-body"
      >
        <el-alert
          v-if="drawerError"
          :title="drawerError"
          type="error"
          show-icon
          :closable="false"
          class="mb"
        />

        <div class="mb batch-picker">
          <span>评估批次：</span>
          <el-select
            v-model="selectedBatch"
            style="width: 380px"
            placeholder="选择评估批次"
          >
            <el-option
              label="最新批次"
              value=""
            />
            <el-option
              v-for="batch in batches"
              :key="batch.job_id"
              :label="`${formatTime(batch.created_at)} · ${batch.job_id}`"
              :value="batch.job_id"
            />
          </el-select>
        </div>

        <el-alert
          v-if="metricsUnavailable"
          :title="'指标不可用：' + metricsUnavailable"
          type="warning"
          show-icon
          :closable="false"
          class="mb"
        />
        <el-alert
          v-if="missingFigures.length"
          title="部分图表暂不可用"
          type="warning"
          show-icon
          :closable="false"
          class="mb"
        />

        <StatGrid
          v-if="metrics"
          :items="metricItems"
        />

        <div
          v-for="fig in figureImages"
          :key="fig.figure_type"
          class="figure"
        >
          <h3>{{ fig.title }}</h3>
          <img
            :src="fig.url"
            :alt="fig.title"
          >
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { getCommits, getFigures, fetchFigureBlob } from '../api'
import { riskColor } from '../utils/risk'
import { loadModelLines } from '../utils/models'
import { FEATURE_GROUPS, featureLabel } from '../utils/features'
import { errText, isRetryable } from '../utils/errors'
import { formatTime } from '../utils/datetime'
import LineModelCascade from '../components/LineModelCascade.vue'
import FilterBar from '../components/FilterBar.vue'
import StatGrid from '../components/StatGrid.vue'

const lines = ref([])
const selectedLine = ref('')
const selectedModel = ref('')

const filters = reactive({ q: '', page: 1, size: 20 })
const timeRange = ref([])

const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const retryable = ref(false)

const featureGroups = FEATURE_GROUPS

function featureValue(value) {
  if (value === null || value === undefined) return '—'
  const number = Number(value)
  if (Number.isNaN(number)) return String(value)
  return Number.isInteger(number) ? String(number) : number.toFixed(4)
}

let requestId = 0
async function load(page = filters.page) {
  if (!selectedModel.value) return
  const id = ++requestId
  filters.page = page
  loading.value = true
  error.value = ''
  retryable.value = false
  try {
    const data = await getCommits({
      page: filters.page,
      size: filters.size,
      q: filters.q.trim() || undefined,
      model_name: selectedModel.value,
      start_time: timeRange.value?.[0] || undefined,
      end_time: timeRange.value?.[1] || undefined,
      with_features: '1'
    })
    if (id !== requestId) return
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    if (id !== requestId) return
    items.value = []
    total.value = 0
    error.value = errText(e)
    retryable.value = isRetryable(e)
  } finally {
    if (id === requestId) loading.value = false
  }
}

function reset() {
  filters.q = ''
  timeRange.value = []
  load(1)
}

// 模型切换整列刷新；未选模型时 load 直接返回，不依赖默认模型
watch(selectedModel, () => {
  requestId++
  if (selectedModel.value) { load(1); return }
  // 清空模型后必须同步清空旧结果，否则页面仍显示上一模型的风险分
  items.value = []; total.value = 0; error.value = ''; loading.value = false
  drawerVisible.value = false
})

// ── 查看抽屉 ──
const drawerVisible = ref(false)
const drawerLoading = ref(false)
const drawerError = ref('')
const metrics = ref(null)
const metricsUnavailable = ref('')
const missingFigures = ref([])
const figureImages = ref([])
const drawerTitle = computed(() =>
  selectedModel.value ? `${selectedModel.value} 性能评估` : '性能评估'
)
const batches = ref([])
const selectedBatch = ref('')
const metricItems = computed(() => metrics.value ? [
  { label: 'AUC', value: fmt(metrics.value.auc) },
  { label: 'AP', value: fmt(metrics.value.ap) },
  { label: 'F1', value: fmt(metrics.value.f1) },
  { label: '精确率', value: fmt(metrics.value.precision) },
  { label: '召回率', value: fmt(metrics.value.recall) },
  { label: '准确率', value: fmt(metrics.value.accuracy) },
  { label: '样本数', value: metrics.value.n },
  { label: '正样本占比', value: `${(metrics.value.pos_rate * 100).toFixed(1)}%` }
] : [])

async function loadFigures() {
  drawerLoading.value = true
  drawerError.value = ''
  metrics.value = null
  metricsUnavailable.value = ''
  missingFigures.value = []
  figureImages.value = []
  try {
    const data = await getFigures({
      model_name: selectedModel.value,
      job_id: selectedBatch.value || undefined
    })
    if (Array.isArray(data.batches)) batches.value = data.batches
    metrics.value = Object.fromEntries((data.metrics || []).map((row) => [row.metric, row.value]))
    metricsUnavailable.value = data.metrics_unavailable || ''
    missingFigures.value = data.missing || []
    const usableFigures = (data.figures || []).filter(f => typeof f.file_path === 'string' && f.file_path)
    missingFigures.value.push(...(data.figures || []).filter(f => !(typeof f.file_path === 'string' && f.file_path)).map(f => f.title || f.figure_type || '未命名图'))
    const urls = await Promise.all(
      usableFigures.map(async (f) => ({
        figure_type: f.figure_type,
        title: f.title,
        url: await fetchFigureBlob(f.file_path)
      }))
    )
    figureImages.value = urls
  } catch (e) {
    drawerError.value = e?.code === 40400 ? '该模型暂无已登记的性能图或指标' : errText(e)
  } finally {
    drawerLoading.value = false
  }
}

watch(selectedBatch, (value, old) => {
  if (drawerVisible.value && value !== old) loadFigures()
})

async function openDrawer() {
  if (!selectedModel.value) return
  drawerVisible.value = true
  selectedBatch.value = ''
  batches.value = []
  await loadFigures()
}

function fmt(v) {
  if (v === null || v === undefined) return '—'
  const n = Number(v)
  return Number.isNaN(n) ? String(v) : n.toFixed(4)
}

// 关闭抽屉时释放 ObjectURL，避免内存泄漏
function revokeUrls() {
  figureImages.value.forEach((f) => f.url && URL.revokeObjectURL(f.url))
  figureImages.value = []
}
watch(drawerVisible, (v) => {
  if (!v) revokeUrls()
})
onBeforeUnmount(revokeUrls)

onMounted(() => {
  loadModelLines().then((l) => {
    lines.value = l
  })
  load()
})
</script>

<style scoped>
.filter-label {
  color: var(--ui-text-muted);
  font-size: var(--ui-font-sm);
  font-weight: 550;
}
.mp-table {
  margin-top: 8px;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
.feat-group {
  margin-bottom: var(--ui-space-3);
}
.feat-group h3 {
  margin: 0 0 var(--ui-space-1);
  font-size: var(--ui-font-sm);
  color: var(--ui-text-muted);
}
.feat-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--ui-space-1);
}
.feat-item {
  padding: 3px 8px;
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  background: var(--ui-surface-subtle);
  color: var(--ui-text-muted);
  font-size: var(--ui-font-sm);
}
.figure {
  margin-bottom: var(--ui-space-5);
}
.figure h3 {
  margin: 0 0 var(--ui-space-2);
  font-size: var(--ui-font-base);
}
.figure img {
  display: block;
  max-width: 880px;
  width: 100%;
  margin: 0 auto;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
}
.drawer-body {
  min-height: 200px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
