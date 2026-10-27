<template>
  <div class="hint">
    <span class="text">{{ text }}</span>
    <span
      v-if="$slots.default"
      class="act"
    >
      <slot />
    </span>
  </div>
</template>

<script setup>
// 页面引导条：一句话说清「这页干什么、下一步做什么」，右侧放主操作。
// 全站统一用这一条，避免各页面各写一段长说明（冗余来源）。
defineProps({
  text: { type: String, required: true }
})
</script>

<style scoped>
.hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 14px;
}
.text {
  color: #6b7280;
  font-size: 13px;
  line-height: 1.6;
}
.act {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}
</style>
