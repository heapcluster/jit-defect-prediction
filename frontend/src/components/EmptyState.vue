<template>
  <div class="empty">
    <div class="icon" aria-hidden="true">◌</div>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.action" class="action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '暂无数据' },
  description: { type: String, default: '' }
})
</script>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 34px 20px;
  text-align: center;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface-muted);
}

.icon {
  font-size: 28px;
  color: var(--text-soft);
}

h3 {
  font-size: 14px;
  font-weight: 700;
}

p {
  color: var(--text-muted);
  font-size: 12.5px;
  max-width: 460px;
  line-height: 1.6;
}

.action {
  margin-top: 6px;
}
</style>
