<template>
  <div>
    <PageHint text="按 PR 看聚合风险（取该 PR 内最高风险提交）；未预测的点「同步 PR 预测」现算。">
      <el-button
        size="small"
        type="primary"
        :loading="syncing"
        @click="sync"
      >
        同步 PR 预测
      </el-button>
      <el-button
        size="small"
        :loading="loading"
        @click="load"
      >
        刷新
      </el-button>
    </PageHint>

    <!-- 只留表格里看不出来的两个聚合值：PR 总数与当前模型在下方的筛选栏里已有 -->
    <div class="stats">
      <StatCard
        label="高风险 PR"
        :value="highRiskCount"
        hint="最高提交达到高阈值"
      />
      <StatCard
        label="待预测"
        :value="unpredictedCount"
        hint="有提交尚未现算"
      />
    </div>

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
    </el-form>

    <!-- 同步进度：一行说清，不铺大段说明 -->
    <el-alert
      v-if="syncing"
      type="info"
      :closable="false"
      class="mb"
    >
      正在逐条现算（约 4 秒/条），已处理 {{ syncDone }} 条，完成后自动刷新。
    </el-alert>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      class="mb"
    />

    <!-- 表格不随 error 卸载：出错时仍保留上一次拉到的数据 -->
    <el-table
      v-loading="loading"
      :data="items"
      class="table"
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
        width="130"
      />
      <el-table-column
        label="风险"
        width="190"
      >
        <template #default="{ row }">
          <div
            v-if="row.risk_score == null"
            class="unpredicted"
          >
            未预测
          </div>
          <div
            v-else
            class="risk-cell"
          >
            <RiskTag
              :level="row.risk_level"
              :score="row.risk_score"
              effect="dark"
            />
            <span :style="{ color: riskColor(row.risk_score) }">
              {{ (row.risk_score * 100).toFixed(1) }}%
            </span>
            <el-tooltip
              v-if="row.reason"
              :content="row.reason"
              placement="top"
            >
              <span class="why">ⓘ</span>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
      <el-table-column
        label="提交"
        width="100"
      >
        <template #default="{ row }">
          {{ row.predicted_count }}/{{ row.commit_count }}
        </template>
      </el-table-column>
      <el-table-column
        label="更新"
        width="170"
      >
        <template #default="{ row }">
          {{ formatTime(row.updated_at) }}
        </template>
      </el-table-column>
    </el-table>

    <el-empty
      v-if="!loading && !error && items.length === 0"
      description="暂无 PR"
    >
      <el-button
        size="small"
        type="primary"
        :loading="syncing"
        @click="sync"
      >
        同步 PR 预测
      </el-button>
    </el-empty>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getPrs, postSyncPrs } from '../api'
import { MODELS } from '../utils/models'
import { riskColor } from '../utils/risk'
import { errText } from '../utils/errors'
import { formatTime } from '../utils/datetime'
import StatCard from '../components/StatCard.vue'
import PageHint from '../components/PageHint.vue'
import RiskTag from '../components/RiskTag.vue'

const router = useRouter()
const models = MODELS
const items = ref([])
const loading = ref(false)
const syncing = ref(false)
const syncDone = ref(0)
const error = ref('')
const filters = reactive({ model_name: '' })

const highRiskCount = computed(
  () => items.value.filter((i) => i.risk_level === '高').length
)
const unpredictedCount = computed(
  () => items.value.filter((i) => i.risk_score == null).length
)

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
  syncDone.value = 0
  error.value = ''
  // 分批触发避免单请求超时；批数按实际 PR 数收敛（PR 少于 30 时不再固定跑满 3 轮，
  // 每轮会给每个 PR 打一次 GitHub 提交清单调用，白耗配额）
  const target = Math.min(30, Math.max(items.value.length, 10))
  try {
    for (let done = 0; done < target; done += 10) {
      await postSyncPrs(10)
      syncDone.value = Math.min(done + 10, target)
    }
  } catch (e) {
    error.value = errText(e)
  } finally {
    syncing.value = false
    // 无论成功与否都重新拉一次：同步可能只完成一部分（失败进 skipped）
    await load()
  }
}

function openPr(row) {
  router.push(`/prs/${row.number}`)
}

onMounted(load)
</script>

<style scoped>
.stats {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.filters {
  margin-bottom: 4px;
}
.mb {
  margin-bottom: 12px;
}
.table {
  cursor: pointer;
  margin-top: 8px;
}
.risk-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}
.unpredicted {
  color: #9aa1ab;
}
.why {
  color: #9aa1ab;
  cursor: help;
}
</style>
