<template>
  <div class="info-card">
    <div
      class="info-grid"
      :class="{ 'cols-3': columns === 3 }"
    >
      <div
        v-for="item in items"
        :key="item.key || item.label"
        class="info-row"
        :class="{ 'span-two': item.span }"
      >
        <span class="info-label">{{ item.label }}</span>
        <span
          class="info-value"
          :class="{ mono: item.mono }"
        >
          <slot
            :name="item.key || item.label"
            :item="item"
          >{{ item.value }}</slot>
        </span>
      </div>
    </div>
    <slot />
  </div>
</template>

<script setup>
// 键值信息卡：预测 / 评估 / 训练 / 收集 / 存储共用同一套标签与数值排版。
defineOptions({ name: 'InfoGrid' })
defineProps({
  // item: { key?, label, value?, mono?, span? }
  items: { type: Array, default: () => [] },
  columns: { type: Number, default: 2 }
})
</script>
