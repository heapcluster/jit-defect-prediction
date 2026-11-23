<template>
  <section class="workbench">
    <el-tabs
      v-model="active"
      aria-label="预测功能子视图"
    >
      <el-tab-pane
        label="预测工具台"
        name="tool"
      >
        <Predict v-if="active === 'tool'" />
      </el-tab-pane>
      <el-tab-pane
        label="风险列表"
        name="risks"
      >
        <RiskList v-if="active === 'risks'" />
      </el-tab-pane>
      <el-tab-pane
        label="趋势看板"
        name="trends"
      >
        <TrendBoard v-if="active === 'trends'" />
      </el-tab-pane>
      <el-tab-pane
        v-if="commitHash"
        label="提交详情"
        name="detail"
      >
        <CommitDetail
          v-if="active === 'detail'"
          :key="commitHash"
          :hash="commitHash"
        />
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Predict from './Predict.vue'
import RiskList from './RiskList.vue'
import TrendBoard from './TrendBoard.vue'
import CommitDetail from './CommitDetail.vue'

defineOptions({ name: 'PredictWorkbench' })
const route = useRoute(), router = useRouter()
const commitHash = computed(() => typeof route.params.hash === 'string' ? route.params.hash : '')
const active = computed({
  get() { return commitHash.value ? 'detail' : ['risks', 'trends'].includes(route.query.section) ? route.query.section : 'tool' },
  set(section) {
    if (section === 'detail') return
    const query = { ...route.query }
    if (section === 'tool') delete query.section
    else query.section = section
    router.push({ path: '/predict', query, hash: route.hash })
  }
})
</script>

<style scoped>
.workbench { min-width: 0; }
</style>
