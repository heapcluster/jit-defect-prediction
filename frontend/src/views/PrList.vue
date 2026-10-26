<template>
  <div>
    <el-form
      :inline="true"
      class="filters"
    >
      <el-form-item label="模型">
        <el-select
          v-model="filters.model_name"
          clearable
          placeholder="默认模型"
          style="width: 160px"
          @change="load"
        >
          <el-option
            v-for="m in models"
            :key="m"
            :label="m"
            :value="m"
          />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          :loading="syncing"
          @click="sync"
        >
          同步最新 PR 预测
        </el-button>
        <el-button
          :loading="loading"
          @click="load"
        >
          刷新
        </el-button>
      </el-form-item>
    </el-form>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
    />

    <!-- 表格不随 error 卸载：出错时仍保留上一次拉到的数据（2026-10-25 修复，
         此前 v-else 会把整表卸载，用户得手动刷新才能看到数据） -->
    <el-table
      v-loading="loading"
      :data="items"
      style="cursor: pointer"
      @row-click="openPr"
    >
      <el-table-column
        prop="number"
        label="PR#"
        width="90"
      />
      <el-table-column
        prop="title"
        label="标题"
        min-width="220"
        show-overflow-tooltip
      />
      <el-table-column
        prop="author"
        label="作者"
        width="140"
      />
      <el-table-column
        label="状态"
        width="90"
      >
        <template #default="{ row }">
          <el-tag :type="row.state === 'open' ? 'success' : 'info'">
            {{ row.state }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column
        label="风险"
        width="160"
      >
        <template #default="{ row }">
          <span
            v-if="row.risk_score == null"
            style="color: #909399"
          >未预测</span>
          <span
            v-else
            :style="{ color: riskColor(row.risk_score), fontWeight: 600 }"
          >
            {{ (row.risk_score * 100).toFixed(1) }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column
        label="提交"
        width="110"
      >
        <template #default="{ row }">
          {{ row.predicted_count }}/{{ row.commit_count }}
        </template>
      </el-table-column>
      <el-table-column
        label="更新时间"
        width="180"
      >
        <template #default="{ row }">
          {{ formatTime(row.updated_at) }}
        </template>
      </el-table-column>
    </el-table>

    <el-empty
      v-if="!loading && !error && items.length === 0"
      description="暂无 PR 或尚未同步预测"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getPrs, postSyncPrs } from '../api'
import { MODELS } from '../utils/models'
import { riskColor } from '../utils/risk'
import { errText } from '../utils/errors'
import { formatTime } from '../utils/datetime'

const router = useRouter()
const models = MODELS
const items = ref([])
const loading = ref(false)
const syncing = ref(false)
const error = ref('')
const filters = reactive({ model_name: '' })

// 最新请求标识：并发时丢弃过期响应，避免旧响应覆盖新结果
let requestId = 0

async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  try {
    const data = await getPrs({ limit: 30, model_name: filters.model_name || undefined })
    if (id !== requestId) return
    items.value = data.items || []
  } catch (e) {
    if (id !== requestId) return
    error.value = errText(e)
  } finally {
    if (id === requestId) loading.value = false
  }
}

async function sync() {
  syncing.value = true
  error.value = ''
  try {
    await postSyncPrs(30)
  } catch (e) {
    error.value = errText(e)
  } finally {
    syncing.value = false
    // 无论同步成功与否都重新拉一次列表：同步可能只完成一部分（单 PR 失败进 skipped），
    // 也要让用户看到已入库的那部分结果
    await load()
  }
}

function openPr(row) {
  router.push(`/prs/${row.number}`)
}

onMounted(load)
</script>

<style scoped>
.filters {
  margin-bottom: 16px;
}
</style>
