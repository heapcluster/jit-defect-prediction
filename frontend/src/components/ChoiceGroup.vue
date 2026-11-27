<template>
  <ul
    class="check-list"
    :class="listClass"
    :aria-label="ariaLabel"
  >
    <li
      v-for="option in options"
      :key="option.key"
      class="check-item"
      :class="[
        itemClass,
        {
          'is-active': isChecked(option.key),
          'is-locked': option.locked
        }
      ]"
      :data-testid="option.testid"
      :title="option.tip || undefined"
    >
      <label
        class="check-label"
        :class="{ 'check-label--stack': stack }"
        :for="idOf(option.key)"
      >
        <input
          :id="idOf(option.key)"
          :name="name"
          :type="multiple ? 'checkbox' : 'radio'"
          :value="option.key"
          :checked="isChecked(option.key)"
          :disabled="disabled || option.disabled"
          @change="onChange(option.key, $event.target.checked)"
        >
        <span class="check-title">
          {{ option.label }}<small
            v-if="option.note"
            class="check-note"
          >{{ option.note }}</small>
        </span>
        <span
          v-if="option.badge"
          class="check-badge"
        >{{ option.badge }}</span>
      </label>
      <p
        v-if="option.summary"
        class="check-summary"
      >
        {{ option.summary }}
      </p>
      <span
        v-if="option.tip"
        class="ui-hover-tip"
        role="tooltip"
      >{{ option.tip }}</span>
      <div
        v-if="$slots.extra && isChecked(option.key)"
        class="check-body"
      >
        <slot
          name="extra"
          :option="option"
        />
      </div>
    </li>
  </ul>
</template>

<script setup>
// 全站唯一的选择卡片组件：训练架构 / 算法、清洗处理项、评估指标、采集来源共用。
// 结构固定为「勾选 + 序号 + 标题 + 徽标 + 摘要 + 参数区」，样式统一由 ui.css 的 .check-* 提供。
// id 统一为 `${name}-${key}`，保持既有表单定位与测试选择器稳定。
defineOptions({ name: 'ChoiceGroup' })
const props = defineProps({
  name: { type: String, required: true },
  options: { type: Array, default: () => [] },
  // multiple 时传数组，单选时传标量
  modelValue: { type: [Array, String, Number, Boolean], default: () => [] },
  multiple: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  ariaLabel: { type: String, default: undefined },
  listClass: { type: String, default: '' },
  itemClass: { type: String, default: '' },
  stack: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue', 'change'])

function idOf(key) {
  return `${props.name}-${key}`
}

function isChecked(key) {
  return props.multiple
    ? Array.isArray(props.modelValue) && props.modelValue.includes(key)
    : props.modelValue === key
}

function onChange(key, checked) {
  if (!props.multiple) {
    emit('update:modelValue', key)
    emit('change', key)
    return
  }
  const current = Array.isArray(props.modelValue) ? props.modelValue : []
  const next = checked
    ? [...new Set([...current, key])]
    : current.filter(item => item !== key)
  emit('update:modelValue', next)
  emit('change', key)
}
</script>
