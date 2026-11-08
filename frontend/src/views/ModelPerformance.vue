<template>
  <div>
    <!-- 模型选择区：架构 → 模型级联 + 查看抽屉 -->
    <el-form
      :inline="true"
      class="filters"
    >
      <el-form-item label="模型">
        <LineModelCascade
          v-model:line="selectedLine"
          v-model:model="selectedModel"
          :lines="lines"
          model-placeholder="默认模型"
        />
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          :disabled="!selectedModel"
          @click="openDrawer"
        >
          查看
        </el-button>
      </el-form-item>
    </el-form>

    <!-- 查询栏：搜索 + 时间范围（表格固定 is_test=1 & with_features=1） -->
    <el-form
      :inline="true"
      class="filters"
    >
      <el-form-item label="搜索">
        <el-input
          v-model="filters.q"
          placeholder="哈希/作者/提交信息"
          clearable
          maxlength="64"
          style="width: 200px"
          @keyup.enter="load(1)"
        />
      </el-form-item>
      <el-form-item label="时间范围">
        <el-date-picker
          v-model="timeRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始"
          end-placeholder="结束"
          style="width: 240px"
        />
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          @click="load(1)"
        >
          查询
        </el-button>
        <el-button @click="reset">
          重置
        </el-button>
      </el-form-item>
    </el-form>

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
        label="14 维特征"
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
              <h4>{{ group.title }}</h4>
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
        label="SZZ 判断"
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
            未打标
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

        <div
          v-if="metrics"
          class="metrics"
        >
          <StatCard
            label="AUC"
            :value="fmt(metrics.auc)"
          />
          <StatCard
            label="AP"
            :value="fmt(metrics.ap)"
          />
          <StatCard
            label="F1"
            :value="fmt(metrics.f1)"
          />
          <StatCard
            label="Precision"
            :value="fmt(metrics.precision)"
          />
          <StatCard
            label="Recall"
            :value="fmt(metrics.recall)"
          />
          <StatCard
            label="Accuracy"
            :value="fmt(metrics.accuracy)"
          />
          <StatCard
            label="样本数"
            :value="metrics.n"
          />
          <StatCard
            label="正样本占比"
            :value="(metrics.pos_rate * 100).toFixed(1) + '%'"
          />
        </div>

        <div
          v-for="fig in figureImages"
          :key="fig.figure_type"
          class="figure"
        >
          <h4>{{ fig.title }}</h4>
          <img
            :src="fig.url"
            :alt="fig.title"
          />
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
import StatCard from '../components/StatCard.vue'

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
      model_name: selectedModel.value || undefined,
      start_time: timeRange.value?.[0] || undefined,
      end_time: timeRange.value?.[1] || undefined,
      with_features: '1',
      is_test: '1'
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

// 模型切换整列刷新；模型不选 = 后端默认模型
watch(selectedModel, () => load(1))

// ── 查看抽屉 ──
const drawerVisible = ref(false)
const drawerLoading = ref(false)
const drawerError = ref('')
const metrics = ref(null)
const figureImages = ref([])
const drawerTitle = computed(() =>
  selectedModel.value ? `${selectedModel.value} 性能评估` : '性能评估'
)

async function openDrawer() {
  if (!selectedModel.value) return
  drawerVisible.value = true
  drawerLoading.value = true
  drawerError.value = ''
  metrics.value = null
  figureImages.value = []
  try {
    const data = await getFigures(selectedModel.value)
    metrics.value = data.metrics || null
    const urls = await Promise.all(
      (data.figures || []).map(async (f) => ({
        figure_type: f.figure_type,
        title: f.title,
        url: await fetchFigureBlob(f.file_path)
      }))
    )
    figureImages.value = urls
  } catch (e) {
    drawerError.value = errText(e)
  } finally {
    drawerLoading.value = false
  }
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
.filters {
  margin-bottom: 4px;
}
.mb {
  margin-bottom: 12px;
}
.mp-table {
  margin-top: 8px;
}
.mono {
  font-family: monospace;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
.feat-group {
  margin-bottom: 10px;
}
.feat-group h4 {
  margin: 0 0 4px;
  font-size: 12px;
  color: #7c838c;
}
.feat-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.feat-item {
  font-size: 12px;
  background: #f4f5f7;
  border-radius: 4px;
  padding: 2px 6px;
}
.metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}
.figure {
  margin-bottom: 20px;
}
.figure h4 {
  margin: 0 0 8px;
  font-size: 14px;
}
.figure img {
  display: block;
  max-width: 880px;
  width: 100%;
  margin: 0 auto;
  border: 1px solid #e2e5ea;
  border-radius: 8px;
}
.drawer-body {
  min-height: 200px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
