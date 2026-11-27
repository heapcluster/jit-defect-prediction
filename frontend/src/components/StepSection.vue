<template>
  <section
    class="step-block"
    :class="[state ? `is-${state}` : undefined, { 'is-sticky': sticky, 'is-collapsed': collapsed }]"
  >
    <div class="step-heading">
      <span
        v-if="index !== '' && index !== null && index !== undefined"
        class="step-index"
        aria-hidden="true"
      >{{ state === 'done' ? '✓' : index }}</span>
      <h3>{{ title }}</h3>
      <span
        v-if="collapsed && (summary || tag)"
        class="step-heading__summary"
      >{{ summary || tag }}</span>
      <span
        v-if="$slots.extra || tag"
        v-show="!collapsed"
        class="step-heading__extra"
      >
        <slot name="extra">
          {{ tag }}
        </slot>
      </span>
      <el-button
        v-if="collapsible && state === 'done'"
        class="step-heading__toggle"
        link
        size="small"
        :aria-expanded="collapsed ? 'false' : 'true'"
        @click="expanded = collapsed"
      >
        {{ collapsed ? '展开' : '收起' }}
      </el-button>
    </div>
    <div
      v-if="!collapsed"
      class="step-body"
    >
      <slot />
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

// 工具页统一步骤块：序号、标题与右侧状态标签共用一套间距和层级。
// state 与顶部 StepRail 保持一致（done / current / upcoming）；
// 已完成的步骤默认折叠为一行摘要，让用户聚焦当前动作，需要时可再展开。
defineOptions({ name: 'StepSection' })
const props = defineProps({
  index: { type: [String, Number], default: '' },
  title: { type: String, required: true },
  tag: { type: String, default: '' },
  state: { type: String, default: '' },
  summary: { type: String, default: '' },
  collapsible: { type: Boolean, default: false },
  // 贴在配置面板底部，滚动时始终可见主操作按钮
  sticky: { type: Boolean, default: false }
})

const expanded = ref(false)
const collapsed = computed(() => props.collapsible && props.state === 'done' && !expanded.value)
</script>

<style scoped>
.step-heading__extra {
  display: inline-flex;
  align-items: center;
  gap: var(--ui-space-2);
  margin-left: auto;
  color: var(--ui-text-muted);
  font-size: var(--ui-font-sm);
  font-weight: 550;
}
.step-heading__summary {
  overflow: hidden;
  margin-right: auto;
  color: var(--ui-text-muted);
  font-size: var(--ui-font-sm);
  font-weight: 450;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.step-heading__toggle {
  flex: 0 0 auto;
  margin-left: var(--ui-space-2);
}
</style>
