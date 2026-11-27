<template>
  <div class="ui-empty">
    <strong>{{ title }}</strong>
    <p v-if="description">
      {{ description }}
    </p>
    <slot />
  </div>
</template>

<script setup>
// 空态：统一虚线容器、标题与说明的层级，页面只传文案。
defineOptions({ name: 'EmptyState' })
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' }
})
</script>
