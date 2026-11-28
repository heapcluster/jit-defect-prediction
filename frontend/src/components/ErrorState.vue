<template>
  <div class="error-state">
    <div class="row">
      <span class="mark">!</span>
      <div class="grow">
        <strong>{{ title }}</strong>
        <p>{{ message }}</p>
      </div>
    </div>
    <el-button v-if="retry" size="small" @click="$emit('retry')">{{ retryLabel }}</el-button>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '操作未完成' },
  message: { type: String, default: '请稍后重试' },
  retry: { type: Boolean, default: true },
  retryLabel: { type: String, default: '重试' }
})

defineEmits(['retry'])
</script>

<style scoped>
.error-state {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 13px 15px;
  border-radius: var(--radius-sm);
  background: var(--danger-soft);
  border: 1px solid rgba(214, 69, 69, 0.2);
  color: #7f1d1d;
  flex-wrap: wrap;
}

.mark {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--danger);
  color: white;
  font-weight: 800;
  flex-shrink: 0;
}

strong {
  font-size: 13px;
}

p {
  margin-top: 3px;
  font-size: 12.5px;
  line-height: 1.5;
}
</style>
