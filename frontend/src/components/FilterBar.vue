<template>
  <div class="ui-filter-bar">
    <div class="ui-filter-bar__controls">
      <slot />
    </div>
    <div
      v-if="$slots.actions"
      class="ui-filter-bar__actions"
    >
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
// 列表页筛选栏：控件左对齐、操作右对齐，窄屏自动换行成单列。
defineOptions({ name: 'FilterBar' })
</script>
