<template>
  <div class="feature-tabs">
    <el-tabs
      :model-value="modelValue"
      class="feature-tabs__nav"
      @tab-change="select"
    >
      <el-tab-pane
        v-for="item in items"
        :key="item.name"
        :label="item.label"
        :name="item.name"
        :disabled="item.disabled"
      />
    </el-tabs>
    <div
      v-if="$slots.extra"
      class="feature-tabs__extra"
    >
      <slot name="extra" />
    </div>
  </div>
</template>

<script setup>
import { useRoute, useRouter } from 'vue-router'

// 统一的功能页子签：section 写入路由 query，保留其他查询参数与 hash。
// 子页面（例如⑤的解释/定位）不使用子签，而是通过 extra 区的跳转按钮进入。
const props = defineProps({
  base: { type: String, required: true },
  items: { type: Array, required: true },
  modelValue: { type: String, required: true }
})

const route = useRoute()
const router = useRouter()

function select(section) {
  const query = { ...route.query }
  if (section === props.items[0]?.name) delete query.section
  else query.section = section
  router.push({ path: props.base, query, hash: route.hash })
}
</script>

<style scoped>
.feature-tabs {
  display: flex;
  align-items: stretch;
  gap: var(--ui-toolbar-gap);
  min-height: var(--ui-toolbar-height);
  margin-bottom: var(--ui-toolbar-gap);
}
.feature-tabs__nav {
  flex: 1;
  min-width: 0;
}
.feature-tabs__nav :deep(.el-tabs__header) {
  height: var(--ui-toolbar-height);
  margin: 0;
}
.feature-tabs__nav :deep(.el-tabs__nav-wrap),
.feature-tabs__nav :deep(.el-tabs__nav) {
  height: var(--ui-toolbar-height);
}
.feature-tabs__nav :deep(.el-tabs__item) {
  height: var(--ui-toolbar-height);
  padding: 0 var(--ui-space-4);
  font-size: var(--ui-font-md);
  font-weight: 550;
  line-height: var(--ui-toolbar-height);
}
.feature-tabs__nav :deep(.el-tabs__item.is-active) {
  font-weight: 650;
}
.feature-tabs__nav :deep(.el-tabs__nav-wrap::after) {
  display: none;
}
.feature-tabs__extra {
  display: flex;
  align-items: center;
  gap: var(--ui-space-2);
  flex-shrink: 0;
}
@media (max-width: 640px) {
  .feature-tabs {
    flex-direction: column;
    align-items: stretch;
  }
  .feature-tabs__nav {
    overflow-x: auto;
  }
}
</style>
