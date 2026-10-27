<template>
  <div>
    <!-- 页面标题由布局层统一提供，这里只留引导与操作，避免同屏出现两次「PR 详情」 -->
    <PageHint text="看这个 PR 各提交的风险；点一行进提交详情看解释与确认标记。">
      <el-button
        size="small"
        @click="$router.push('/prs')"
      >
        返回列表
      </el-button>
    </PageHint>

    <div
      v-if="pr"
      class="pr-head"
    >
      <h2>#{{ pr.number }} {{ pr.title }}</h2>
      <p class="meta">
        作者 {{ pr.author }} · 状态
        <el-tag :type="pr.state === 'open' ? 'success' : 'info'">
          {{ pr.state }}
        </el-tag>
        <el-link
          :href="pr.html_url"
          target="_blank"
          type="primary"
        >
          GitHub
        </el-link>
      </p>
    </div>

    <el-form
      :inline="true"
      class="filters"
    >
      <el-form-item label="模型">
        <el-select
          v-model="modelName"
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
    </el-form>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
    />

    <!-- 表格不随 error 卸载：出错时仍保留上一次拉到的数据（2026-10-25 修复） -->
    <el-table
      v-loading="loading"
      :data="commits"
      style="cursor: pointer"
      @row-click="openCommit"
    >
      <el-table-column
        label="Commit"
        width="120"
      >
        <template #default="{ row }">
          {{ row.sha.slice(0, 8) }}
        </template>
      </el-table-column>
      <el-table-column
        prop="message"
        label="提交说明"
        min-width="260"
        show-overflow-tooltip
      />
      <el-table-column
        prop="author"
        label="作者"
        width="140"
      />
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
        label="预测时间"
        width="180"
      >
        <template #default="{ row }">
          {{ formatDateTime(row.predicted_at) }}
        </template>
      </el-table-column>
    </el-table>

    <el-empty
      v-if="!loading && !error && commits.length === 0"
      description="该 PR 暂无提交或未同步预测"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPrDetail } from '../api'
import { MODELS } from '../utils/models'
import { riskColor } from '../utils/risk'
import { errText } from '../utils/errors'
import { formatDateTime } from '../utils/datetime'
import PageHint from '../components/PageHint.vue'

const route = useRoute()
const router = useRouter()
const models = MODELS
const pr = ref(null)
const commits = ref([])
const loading = ref(false)
const error = ref('')
const modelName = ref('')

// 最新请求标识：并发时丢弃过期响应，避免旧响应覆盖新结果
let requestId = 0

async function load() {
  const id = ++requestId
  loading.value = true
  error.value = ''
  try {
    const data = await getPrDetail(route.params.number, { model_name: modelName.value || undefined })
    if (id !== requestId) return
    pr.value = data
    commits.value = data.commits || []
  } catch (e) {
    if (id !== requestId) return
    pr.value = null
    commits.value = []
    error.value = errText(e)
  } finally {
    if (id === requestId) loading.value = false
  }
}

function openCommit(row) {
  if (row.sha) router.push(`/commit/${row.sha}`)
}

onMounted(load)
watch(() => route.params.number, load)
</script>

<style scoped>
.pr-head {
  margin: 12px 0 16px;
}
.meta {
  color: var(--el-text-color-regular);
}
.filters {
  margin-bottom: 16px;
}
</style>
