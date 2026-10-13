<template>
  <div class="page">
    <!-- 筛选区：参数名与 docs/backend/api-spec.md §三.1 逐字一致，前端不改名、不自造参数 -->
    <el-form :inline="true" class="filters">
      <el-form-item label="模型">
        <el-select
          v-model="filters.model_name"
          placeholder="全部模型"
          clearable
          style="width: 170px"
        >
          <el-option v-for="m in MODEL_OPTIONS" :key="m" :label="m" :value="m" />
        </el-select>
      </el-form-item>
      <el-form-item label="最低风险">
        <el-input-number
          v-model="filters.min_risk"
          :min="0"
          :max="1"
          :step="0.05"
          :precision="2"
          controls-position="right"
          style="width: 140px"
        />
      </el-form-item>
      <el-form-item label="时间范围">
        <el-date-picker
          v-model="timeRange"
          type="datetimerange"
          range-separator="至"
          start-placeholder="起始"
          end-placeholder="截止"
          :value-format="DATETIME_FORMAT"
          style="width: 360px"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="search(1)">查询</el-button>
        <el-button :disabled="loading" @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 排序固定按 risk_score 降序（契约三 §三.1），不提供排序切换 -->
    <el-table
      v-loading="loading"
      :data="items"
      border
      stripe
      class="risk-table"
      @row-click="goDetail"
    >
      <template #empty>
        <span>{{ searched ? '当前筛选条件下没有提交' : '暂无数据' }}</span>
      </template>
      <el-table-column label="风险" width="110" align="center">
        <template #default="{ row }">
          <span class="risk" :class="riskClass(row.risk_score)">{{ formatPct(row.risk_score) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="提交哈希" min-width="140">
        <template #default="{ row }">
          <el-tooltip :content="row.commit_hash" placement="top">
            <span class="hash" @click.stop="copy(row.commit_hash)">{{ shortHash(row.commit_hash) }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="author_name" label="作者" min-width="120" show-overflow-tooltip />
      <el-table-column label="提交时间" min-width="165">
        <template #default="{ row }">{{ formatTime(row.committed_at) }}</template>
      </el-table-column>
      <el-table-column label="提交信息" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">{{ row.message || '—' }}</template>
      </el-table-column>
      <el-table-column prop="model_name" label="模型" min-width="110" />
    </el-table>

    <div class="pager">
      <span class="total">共 {{ total }} 条</span>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="sizes, prev, pager, next"
        background
        @current-change="search"
        @size-change="onSizeChange"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getCommits } from '../api'
import { handleError } from '../utils/feedback'
import { formatPct, riskClass, shortHash, formatTime } from '../utils/format'
import { MODEL_OPTIONS, DEFAULT_PAGE_SIZE, DATETIME_FORMAT } from '../constants'

const router = useRouter()

const loading = ref(false)
const searched = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(DEFAULT_PAGE_SIZE)
const timeRange = ref(null)
const filters = reactive({ model_name: '', min_risk: undefined })

// 只传契约定义的参数：page / size / min_risk / model_name / start_time / end_time
function buildParams() {
  const params = { page: page.value, size: size.value }
  if (filters.model_name) params.model_name = filters.model_name
  if (filters.min_risk !== undefined && filters.min_risk !== null && filters.min_risk !== '') {
    params.min_risk = filters.min_risk
  }
  if (timeRange.value && timeRange.value.length === 2) {
    params.start_time = timeRange.value[0]
    params.end_time = timeRange.value[1]
  }
  return params
}

async function load() {
  loading.value = true
  try {
    const data = await getCommits(buildParams())
    items.value = (data && data.items) || []
    total.value = (data && data.total) || 0
    searched.value = true
  } catch (err) {
    // 空数据不是错误：只有 code !== 0 或网络失败才提示（pages.md §5）
    handleError(err)
  } finally {
    loading.value = false
  }
}

function search(target) {
  if (typeof target === 'number') page.value = target
  load()
}

function onSizeChange() {
  page.value = 1
  load()
}

function reset() {
  filters.model_name = ''
  filters.min_risk = undefined
  timeRange.value = null
  search(1)
}

function goDetail(row) {
  router.push(`/commit/${row.commit_hash}`)
}

function copy(hash) {
  if (!hash || !navigator.clipboard) return
  navigator.clipboard.writeText(hash).then(
    () => ElMessage.success('已复制完整提交哈希'),
    () => ElMessage.warning('复制失败，请手动选择')
  )
}

onMounted(load)
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filters {
  padding: 12px 12px 0;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}
.risk-table :deep(.el-table__row) {
  cursor: pointer;
}
.risk {
  font-weight: 600;
}
.risk.high {
  color: #f56c6c;
}
.risk.mid {
  color: #e6a23c;
}
.risk.low {
  color: #409eff;
}
.risk.none {
  color: #909399;
}
.hash {
  font-family: monospace;
  cursor: copy;
  border-bottom: 1px dashed var(--el-border-color);
}
.pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
}
.total {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
