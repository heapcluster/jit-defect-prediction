<template>
  <section class="workbench">
    <el-tabs
      v-model="active"
      aria-label="评估功能子视图"
    >
      <el-tab-pane
        label="评估工具台"
        name="tool"
      >
        <Evaluate v-if="active === 'tool'" />
      </el-tab-pane>
      <el-tab-pane
        label="模型性能"
        name="models"
      >
        <ModelPerformance v-if="active === 'models'" />
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Evaluate from './Evaluate.vue'
import ModelPerformance from './ModelPerformance.vue'

defineOptions({ name: 'EvaluateWorkbench' })
const route = useRoute(), router = useRouter()
const active = computed({
  get() { return route.query.section === 'models' ? 'models' : 'tool' },
  set(section) {
    const query = { ...route.query }
    if (section === 'tool') delete query.section
    else query.section = section
    router.push({ path: '/evaluate', query, hash: route.hash })
  }
})
</script>

<style scoped>
.workbench { min-width: 0; }
</style>
