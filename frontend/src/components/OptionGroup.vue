<template>
  <fieldset class="option-group">
    <legend class="option-group__legend">
      {{ title }}
      <span
        v-if="description"
        class="option-group__description"
      >{{ description }}</span>
    </legend>
    <div class="option-group__grid">
      <label
        v-for="option in options"
        :key="option.key"
        class="option-group__item"
        :class="{ 'option-group__item--checked': modelValue.includes(option.key) }"
      >
        <input
          type="checkbox"
          :value="option.key"
          :checked="modelValue.includes(option.key)"
          :disabled="disabled"
          @change="toggle(option.key, $event.target.checked)"
        >
        <span class="option-group__copy">
          <strong>{{ option.label || option.key }}</strong>
          <small v-if="option.description">{{ option.description }}</small>
        </span>
      </label>
    </div>
  </fieldset>
</template>

<script setup>
defineOptions({ name: 'OptionGroup' })
const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  modelValue: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

function toggle(key, checked) {
  const next = checked
    ? [...new Set([...props.modelValue, key])]
    : props.modelValue.filter(item => item !== key)
  emit('update:modelValue', next)
}
</script>

<style scoped>
.option-group {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}
.option-group__legend {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--ui-space-2);
  padding: 0;
  margin-bottom: var(--ui-space-2);
  font-size: var(--ui-font-sm);
  font-weight: 650;
  color: var(--ui-text);
}
.option-group__description {
  font-size: var(--ui-font-sm);
  font-weight: 400;
  color: var(--ui-text-muted);
}
.option-group__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: var(--ui-space-2);
}
.option-group__item {
  display: flex;
  align-items: flex-start;
  gap: var(--ui-space-2);
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-surface);
  cursor: pointer;
  transition: border-color 120ms ease, background-color 120ms ease;
}
.option-group__item:hover {
  border-color: var(--ui-primary);
}
.option-group__item--checked {
  border-color: var(--ui-primary);
  background: var(--ui-primary-soft);
}
.option-group__item input {
  margin: 2px 0 0;
  accent-color: var(--ui-primary);
}
.option-group__copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}
.option-group__copy strong {
  font-size: var(--ui-font-sm);
  font-weight: 600;
  line-height: 1.4;
}
.option-group__copy small {
  color: var(--ui-text-muted);
  font-size: var(--ui-font-sm);
  line-height: 1.4;
}
@media (prefers-reduced-motion: reduce) {
  .option-group__item {
    transition: none;
  }
}
</style>
