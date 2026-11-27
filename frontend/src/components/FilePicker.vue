<template>
  <div
    class="file-picker"
    :class="{ 'is-disabled': disabled }"
  >
    <span
      v-if="label"
      class="file-picker__label"
    >{{ label }}</span>
    <div class="file-picker__row">
      <button
        type="button"
        class="file-picker__button"
        :aria-label="ariaLabel"
        :disabled="disabled"
        @click="open"
      >
        {{ files.length ? '重新选择' : '选择文件' }}
      </button>
      <span class="file-picker__hint">{{ hint || (multiple ? '支持多选' : '') }}</span>
    </div>
    <ul
      v-if="files.length"
      class="file-picker__files"
      role="status"
    >
      <li
        v-for="file in files"
        :key="file.name"
      >
        {{ file.name }}
      </li>
    </ul>
    <input
      :id="inputId"
      ref="input"
      type="file"
      :accept="accept"
      :multiple="multiple"
      :aria-label="ariaLabel"
      :disabled="disabled"
      class="file-picker__input"
      @change="onChange"
    >
  </div>
</template>

<script setup>
import { ref } from 'vue'

// 文件选择器：数据导入与工具入口共用，支持单文件 / 多文件与自定义说明。
defineOptions({ name: 'FilePicker' })
const props = defineProps({
  inputId: { type: String, default: undefined },
  label: { type: String, default: '数据文件' },
  ariaLabel: { type: String, default: '数据文件' },
  files: { type: Array, default: () => [] },
  accept: { type: String, default: '.csv,.xlsx' },
  hint: { type: String, default: '' },
  multiple: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['select'])
const input = ref(null)

function open() {
  input.value?.click()
}

function onChange(event) {
  const picked = Array.from(event.target.files || [])
  emit('select', props.multiple ? picked : picked.slice(0, 1))
  event.target.value = ''
}
</script>

<style scoped>
.file-picker {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: var(--ui-space-2);
}
.file-picker__label {
  color: var(--ui-text);
  font-size: var(--ui-font-md);
  font-weight: 600;
}
.file-picker__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ui-space-3);
  min-width: 0;
}
.file-picker__button {
  min-height: 36px;
  flex: 0 0 auto;
  padding: 0 var(--ui-space-4);
  border: 1px solid var(--ui-border-strong);
  border-radius: var(--ui-radius-sm);
  background: var(--ui-surface);
  color: var(--ui-text);
  font: inherit;
  font-size: var(--ui-font-sm);
  font-weight: 600;
  cursor: pointer;
  transition: border-color 120ms ease, color 120ms ease, background-color 120ms ease;
}
.file-picker__button:hover:not(:disabled) {
  border-color: var(--ui-primary);
  background: var(--ui-primary-soft);
  color: var(--ui-primary);
}
.file-picker__button:focus-visible {
  outline: 2px solid var(--ui-primary);
  outline-offset: 2px;
}
.file-picker__button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.file-picker__hint {
  min-width: 0;
  color: var(--ui-text-muted);
  font-size: var(--ui-font-hint);
  overflow-wrap: anywhere;
}
.file-picker__files {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0;
  margin: 0;
  list-style: none;
}
.file-picker__files li {
  max-width: 100%;
  padding: 3px 10px;
  border: 1px solid var(--ui-border);
  border-radius: 999px;
  background: var(--ui-surface-subtle);
  color: var(--ui-text-muted);
  font-size: var(--ui-font-hint);
  overflow-wrap: anywhere;
}
.file-picker__input {
  display: none;
}
</style>
