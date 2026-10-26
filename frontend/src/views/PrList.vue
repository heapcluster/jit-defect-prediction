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

    <!-- 加载台：现算很贵，把成本和进度讲清楚 -->
    <el-alert
      v-if="syncing"
      type="info"
      :closable="false"
      class="sync-tip"
    >
      <p class="sync-msg">
        正在逐条现算特征并用真实模型预测（每条提交约 15 秒），已处理 {{ syncDone }} 条…
        <br>
        页面数据会在同步完成后自动刷新；期间可以切到别的页面，不用守着。
      </p>
    </el-alert>

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
        width="210"
      >
        <template #default="{ row }">
          <el-tooltip
            v-if="row.risk_score == null"
            content="该 PR 的提交尚未预测：点上方「同步最新 PR 预测」按需现算"
            placement="top"
          >
            <span style="color: #909399">未预测</span>
          </el-tooltip>
          <div
            v-else
            style="display: flex; align-items: center; gap: 6px"
          >
            <el-tag
              :type="riskTag(row.risk_score)"
              effect="dark"
              size="small"
            >
              {{ row.risk_level || riskLevel(row.risk_score) }}
            </el-tag>
            <span :style="{ color: riskColor(row.risk_score), fontWeight: 600 }">
              {{ (row.risk_score * 100).toFixed(1) }}%
            </span>
            <el-tooltip
              v-if="row.reason"
              :content="row.reason"
              placement="top"
            >
              <span style="color: #909399; cursor: help">ⓘ</span>
            </el-tooltip>
          </div>
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
import { riskColor, riskLevel, riskTag } from '../utils/risk'
import { errText } from '../utils/errors'
import { formatTime } from '../utils/datetime'

const router = useRouter()
const models = MODELS
const items = ref([])
const loading = ref(false)
const syncing = ref(false)
const syncDone = ref(0)
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
  syncDone.value = 0
  error.value = ''
  try {
    // 分批触发：一次 30 个 PR 的提交现算会顶到前端 300s 超时，改成 3 批 × 10
    for (let done = 0; done < 30; done += 10) {
      await postSyncPrs(10)
      syncDone.value = done + 10
    }
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
.sync-tip {
  margin-bottom: 12px;
}
.sync-msg {
  margin: 0;
  line-height: 1.7;
}
</style>
