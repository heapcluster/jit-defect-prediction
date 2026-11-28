<template>
  <el-drawer
    :model-value="modelValue"
    :title="asset?.name || '资产详情'"
    size="560px"
    destroy-on-close
    @update:model-value="$emit('update:modelValue', $event)"
    @open="load"
  >
    <div v-if="asset" class="drawer">
      <div class="row wrap">
        <span class="pill primary">{{ asset.type === 'dataset' ? '数据集' : '模型' }}</span>
        <span class="pill">{{ badgeLabel }}</span>
        <span class="pill" :class="statusType(asset.status)">{{ STATUS[asset.status] || asset.status }}</span>
      </div>

      <div v-if="asset.type === 'dataset'" class="stack">
        <div class="meta-grid">
          <div><span>模型线</span><strong>{{ LINE[detail?.line] || '—' }}</strong></div>
          <div><span>样本</span><strong>{{ detail?.sample_count ?? asset.sample_count ?? '—' }}</strong></div>
          <div><span>正 / 负</span><strong>{{ detail?.pos_count ?? '—' }} / {{ detail?.neg_count ?? '—' }}</strong></div>
          <div><span>仓库</span><strong class="mono">{{ detail?.repo_url || '—' }}</strong></div>
          <div><span>分支</span><strong>{{ detail?.branch || '—' }}</strong></div>
          <div><span>生成时间</span><strong>{{ formatTime(asset.created_at) }}</strong></div>
        </div>

        <div class="row-between">
          <strong>成员</strong>
          <div class="row">
            <el-button
              v-if="asset.badge === 'prediction' && firstHash"
              size="small"
              type="primary"
              plain
              @click="openResult"
            >
              查看结果
            </el-button>
            <el-button size="small" @click="$emit('download', asset)">下载</el-button>
          </div>
        </div>

        <el-table v-loading="loading" :data="detail?.members?.items || []" size="small" height="360" border>
          <el-table-column
            v-for="column in displayColumns"
            :key="column"
            :prop="column"
            :label="column"
            min-width="130"
            show-overflow-tooltip
          >
            <template #default="{ row }">
              <span :class="{ mono: column === 'commit_id' || column === 'commit_hash' }">
                {{ cell(row[column], column) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
        <div class="row-between">
          <span class="soft">仅展示核心列，完整数据请下载。</span>
          <el-pagination
            v-if="(detail?.members?.total || 0) > pageSize"
            v-model:current-page="page"
            :page-size="pageSize"
            :total="detail?.members?.total || 0"
            layout="prev, pager, next"
            small
            @current-change="loadMembers"
          />
        </div>
      </div>

      <div v-else class="stack">
        <div class="meta-grid">
          <div><span>模型线</span><strong>{{ LINE[asset.badge] || asset.badge || '—' }}</strong></div>
          <div><span>算法</span><strong class="mono">{{ asset.algo || '—' }}</strong></div>
          <div><span>框架</span><strong>{{ asset.framework || '—' }}</strong></div>
          <div><span>格式</span><strong>{{ asset.format ? `.${asset.format}` : '—' }}</strong></div>
          <div><span>文件大小</span><strong>{{ sizeText }}</strong></div>
          <div><span>生成时间</span><strong>{{ formatTime(asset.created_at) }}</strong></div>
        </div>

        <strong>指标</strong>
        <el-table :data="metricRows" size="small" border>
          <el-table-column prop="name" label="指标" width="120" />
          <el-table-column label="训练" align="right">
            <template #default="{ row }">{{ formatPercent(row.train) }}</template>
          </el-table-column>
          <el-table-column label="验证" align="right">
            <template #default="{ row }">{{ formatPercent(row.valid) }}</template>
          </el-table-column>
        </el-table>

        <div class="row">
          <el-button type="primary" @click="$emit('download', asset)">下载模型文件</el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getDataset } from '../api/datasets'
import { formatPercent, formatTime, LINE, STATUS, statusType } from '../utils/format'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  asset: { type: Object, default: null }
})

defineEmits(['update:modelValue', 'download'])

const router = useRouter()
const detail = ref(null)
const loading = ref(false)
const page = ref(1)
const pageSize = 20

const badgeLabel = computed(() => {
  if (!props.asset) return '—'
  if (props.asset.type === 'dataset') return SOURCE_LABEL[props.asset.badge] || props.asset.badge || '—'
  return LINE[props.asset.badge] || props.asset.badge || '—'
})

const SOURCE_LABEL = {
  git_repo: '原始',
  upload: '导入清洗',
  clean: '清洗',
  split: '测试集',
  prediction: '预测结果'
}

const CORE = ['commit_id', 'commit_hash', 'commit_time', 'author_name', 'bug']

const displayColumns = computed(() => {
  const columns = detail.value?.columns || []
  if (props.asset?.badge === 'prediction') return columns
  const picked = columns.filter((column) => CORE.includes(column))
  const features = columns.filter((column) => !CORE.includes(column) && column !== 'project' && column !== 'author_email' && column !== 'commit_message')
  return [...picked.slice(0, 4), ...features.slice(0, 5)]
})

const firstHash = computed(() => {
  const items = detail.value?.members?.items || []
  return items[0]?.commit_hash || null
})

const metricRows = computed(() => {
  const metrics = props.asset?.metrics || {}
  const train = metrics.train || {}
  const valid = metrics.valid || {}
  return ['accuracy', 'precision', 'recall', 'f1', 'auc', 'mcc'].map((name) => ({
    name: name.toUpperCase(),
    train: train[name],
    valid: valid[name]
  }))
})

const sizeText = computed(() => {
  const size = props.asset?.size_bytes
  if (!size) return '—'
  if (size > 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`
  return `${(size / 1024).toFixed(1)} KB`
})

function cell(value, column) {
  if (value === null || value === undefined || value === '') return '—'
  if (column === 'risk_score') return Number(value).toFixed(4)
  if (column === 'predicted_label') return Number(value) === 1 ? '缺陷' : '正常'
  if (column === 'bug') return Number(value) === 1 ? '缺陷' : '正常'
  return String(value)
}

async function loadMembers() {
  if (!props.asset || props.asset.type !== 'dataset') return
  loading.value = true
  try {
    detail.value = await getDataset(props.asset.id, { page: page.value, page_size: pageSize })
  } finally {
    loading.value = false
  }
}

function load() {
  detail.value = null
  page.value = 1
  if (props.asset?.type === 'dataset') loadMembers()
}

function openResult() {
  if (!props.asset?.source_job_id || !firstHash.value) return
  router.push(`/predict/${props.asset.source_job_id}/commit/${firstHash.value}`)
}
</script>

<style scoped>
.drawer {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.meta-grid > div {
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-grid span {
  font-size: 11.5px;
  color: var(--text-soft);
}

.meta-grid strong {
  font-size: 13px;
  word-break: break-all;
}
</style>
