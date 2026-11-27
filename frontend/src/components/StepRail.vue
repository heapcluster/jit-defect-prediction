<template>
  <ol
    class="step-rail"
    :aria-label="ariaLabel"
  >
    <li
      v-for="(step, index) in steps"
      :key="step.title"
      class="step-rail__item"
      :class="stateOf(index)"
      :aria-current="index === active ? 'step' : undefined"
    >
      <span
        class="step-rail__marker"
        aria-hidden="true"
      >{{ index < active ? '✓' : index + 1 }}</span>
      <span class="step-rail__copy">
        <span class="step-rail__title">{{ step.title }}</span>
        <span
          v-if="step.note"
          class="step-rail__note"
        >{{ step.note }}</span>
      </span>
      <span
        v-if="index < steps.length - 1"
        class="step-rail__line"
        aria-hidden="true"
      />
    </li>
  </ol>
</template>

<script setup>
// 工具页顶部的步骤轨道：只做进度指引，不承担导航，避免和左侧菜单争夺层级。
defineOptions({ name: 'StepRail' })
const props = defineProps({
  steps: { type: Array, default: () => [] },
  active: { type: Number, default: 0 },
  ariaLabel: { type: String, default: '操作步骤' }
})

function stateOf(index) {
  if (index < props.active) return 'is-done'
  if (index === props.active) return 'is-current'
  return 'is-upcoming'
}
</script>
