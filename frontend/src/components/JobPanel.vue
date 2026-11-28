<template>
  <div v-if="job" class="job-panel">
    <div class="job-top">
      <div class="row">
        <span class="dot" :class="statusClass" />
        <strong>{{ statusText }}</strong>
        <span v-if="job.current_stage" class="muted">· {{ job.current_stage }}</span>
      </div>
      <div class="row">
        <span class="mono soft">{{ job.job_id }}</span>
        <span class="muted mono">{{ elapsed }}s</span>
        <el-button v-if="isRunning" size="small" @click="$emit('cancel')">取消</el-button>
      </div>
    </div>
    <el-progress
      :percentage="progress"
      :status="isFailed ? 'exception' : isSuccess ? 'success' : undefined"
      :stroke-width="8"
      :show-text="false"
    />
    <div class="job-meta">
      <span>进度 {{ job.done }} / {{ job.total || '—' }}</span>
      <span v-if="job.error_message" class="error">{{ job.error_message }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { JOB_STATUS } from '../utils/format'

const props = defineProps({
  job: { type: Object, default: null },
  elapsed: { type: Number, default: 0 },
  progress: { type: Number, default: 0 },
  isRunning: { type: Boolean, default: false },
  isSuccess: { type: Boolean, default: false },
  isFailed: { type: Boolean, default: false }
})

defineEmits(['cancel'])

const statusText = computed(() => JOB_STATUS[props.job?.status] || props.job?.status || '')
const statusClass = computed(() => ({
  running: props.isRunning,
  success: props.isSuccess,
  failed: props.isFailed
}))
</script>

<style scoped>
.job-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  border-radius: var(--radius);
  background: var(--surface-muted);
  border: 1px solid var(--border);
}

.job-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-soft);
}

.dot.running {
  background: var(--warning);
  box-shadow: 0 0 0 4px rgba(183, 121, 31, 0.14);
  animation: pulse 1.4s infinite;
}

.dot.success {
  background: var(--success);
}

.dot.failed {
  background: var(--danger);
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.45;
  }
}

.job-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
  flex-wrap: wrap;
}

.error {
  color: var(--danger);
  font-weight: 600;
}
</style>
