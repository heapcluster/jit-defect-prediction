<template>
  <Teleport
    v-if="!hideTabs"
    to="#page-header-tabs"
    :disabled="!headerTabsAvailable"
  >
    <FeatureTabs
      :base="base"
      :items="items"
      :model-value="modelValue"
      data-pane="wide"
    >
      <template
        v-if="$slots.extra"
        #extra
      >
        <slot name="extra" />
      </template>
    </FeatureTabs>
  </Teleport>
  <div
    class="panel config-panel tool-workspace__pane"
    data-pane="wide"
    role="tabpanel"
    :aria-label="title || current?.label || ''"
  >
    <slot :name="paneName" />
  </div>
  <!-- 进度、结果与文件合并成同一张卡片，避免页面下方散落多个面板。 -->
  <section
    v-if="$slots.after"
    id="tool-results"
    class="tool-workspace__after"
    data-pane="wide"
    aria-label="运行结果"
  >
    <slot name="after" />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import FeatureTabs from './FeatureTabs.vue'

// 所有标签页共用同一个面板节点：切换时只替换 slot 内容，容器不重建，
// 因此边距、标题位置和宽度在切换过程中保持不变。
const props = defineProps({
  base: { type: String, default: '' },
  items: { type: Array, default: () => [] },
  modelValue: { type: String, required: true },
  title: { type: String, default: '' },
  // 工具页不再提供历史子签，直接渲染单页配置面板。
  hideTabs: { type: Boolean, default: false }
})
const headerTabsAvailable = typeof document !== 'undefined' && Boolean(document.querySelector('#page-header-tabs'))

const current = computed(() => props.items.find(item => item.name === props.modelValue))
// pane 允许多个标签共用同一个内容面板（例如清洗页的两种输入方式）
const paneName = computed(() => current.value?.pane || props.modelValue)
</script>

<style scoped>
.tool-workspace__pane {
  min-width: 0;
  padding: 20px 24px;
}
.tool-workspace__pane > :deep(.el-alert) {
  margin-bottom: var(--ui-space-4);
}
.tool-workspace__pane > :deep(.el-pagination) {
  margin-top: var(--ui-space-4);
}
/* 子页面原有的多块面板降级为区块，避免统一面板内出现双层卡片 */
.tool-workspace__pane :deep(.panel) {
  margin: 0;
  padding: 0 0 var(--ui-space-5);
  border: 0;
  border-bottom: 1px solid var(--ui-border);
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.tool-workspace__pane :deep(.panel:last-child) {
  border-bottom: 0;
  padding-bottom: 0;
}

/* 结果区：一张卡片内部用分隔线承载进度 / 结果 / 文件三个区块 */
.tool-workspace__after {
  min-width: 0;
  margin-top: var(--ui-space-4);
  overflow: hidden;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-xl);
  background: var(--ui-surface);
  box-shadow: var(--ui-shadow-sm);
  scroll-margin-top: 84px;
}
.tool-workspace__after :deep(.panel) {
  margin: 0;
  padding: 20px 24px;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
.tool-workspace__after :deep(.panel + .panel) {
  margin-top: 0;
  border-top: 1px solid var(--ui-border);
}
.tool-workspace__after :deep(.section-heading) {
  margin-bottom: var(--ui-space-3);
}

@media (max-width: 768px) {
  .tool-workspace__pane,
  .tool-workspace__after :deep(.panel) {
    padding: 18px;
  }
}
</style>
