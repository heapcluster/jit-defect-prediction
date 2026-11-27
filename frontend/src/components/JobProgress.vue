<template>
  <section
    class="panel"
    aria-live="polite"
    data-pane="wide"
    :data-testid="testId"
  >
    <div class="section-heading">
      <h2>{{ title }}</h2>
    </div>
    <el-progress
      v-if="job"
      :percentage="percentage"
      :stroke-width="10"
      :color="success ? 'var(--ui-success)' : undefined"
    />
    <p class="progress-text">
      {{ text }}
    </p>
    <el-alert
      v-if="job?.error_log"
      :title="job.error_log"
      type="error"
      :closable="false"
    />
    <div
      v-if="job"
      class="actions"
    >
      <el-button
        v-if="job.status === 'failed'"
        :data-testid="retryTestId"
        :disabled="retryDisabled"
        @click="$emit('retry')"
      >
        重试原任务
      </el-button><el-button
        v-if="running"
        :data-testid="cancelTestId"
        :disabled="cancelDisabled"
        @click="$emit('cancel')"
      >
        取消任务
      </el-button>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { jobPercentage } from '../utils/progress'

defineOptions({ name: 'JobProgress' })
const props = defineProps({
  title: { type: String, required: true },
  testId: { type: String, required: true },
  job: { type: Object, default: null },
  text: { type: String, default: '' },
  retryTestId: { type: String, default: undefined },
  cancelTestId: { type: String, default: undefined },
  retryDisabled: { type: Boolean, default: false },
  cancelDisabled: { type: Boolean, default: false }
})
defineEmits(['retry', 'cancel'])

// 不设置 status=success：成功时右侧仍显示百分比，而不是对勾。
const percentage = computed(() => jobPercentage(props.job))
const running = computed(() => ['queued', 'running'].includes(props.job?.status))
const success = computed(() => props.job?.status === 'success')
</script>
