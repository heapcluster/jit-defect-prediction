<template>
  <div class="step-block">
    <div class="step-heading">
      <span class="step-index">01</span><h3>选择输入</h3>
    </div>
    <div class="fields">
      <label :for="sourceSelectId">{{ sourceLabel }}
        <select
          :id="sourceSelectId"
          :value="sourceId"
          :disabled="disabled"
          @change="$emit('update:sourceId', $event.target.value)"
        >
          <option value="">
            {{ sources.length ? '请选择上一步产物' : '暂无可用产物' }}
          </option>
          <option
            v-for="item in sources"
            :key="item.value"
            :value="item.value"
          >
            {{ item.label }}
          </option>
        </select>
      </label>
    </div>
  </div>
</template>

<script setup>
defineOptions({ name: 'SourceTabs' })
defineProps({
  sources: { type: Array, default: () => [] },
  sourceId: { type: String, default: '' },
  sourceLabel: { type: String, default: '上一步产物' },
  sourceSelectId: { type: String, default: 'source-file' },
  disabled: { type: Boolean, default: false }
})
defineEmits(['update:sourceId'])
</script>
