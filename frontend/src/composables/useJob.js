import { computed, onUnmounted, ref } from 'vue'
import { cancelJob, getJob } from '../api/jobs'

export function useJob() {
  const job = ref(null)
  const elapsed = ref(0)
  const error = ref('')
  let timer = null
  let ticker = null
  let startAt = 0

  const status = computed(() => job.value?.status || 'idle')
  const isRunning = computed(() => status.value === 'queued' || status.value === 'running')
  const isSuccess = computed(() => status.value === 'success')
  const isFailed = computed(() => status.value === 'failed')
  const isCancelled = computed(() => status.value === 'cancelled')
  const progress = computed(() => {
    if (!job.value || !job.value.total) return 0
    return Math.min(100, Math.round((job.value.done / job.value.total) * 100))
  })

  function stop() {
    if (timer) clearTimeout(timer)
    if (ticker) clearInterval(ticker)
    timer = null
    ticker = null
  }

  async function poll(jobId) {
    try {
      const data = await getJob(jobId)
      job.value = data
      if (['success', 'failed', 'cancelled'].includes(data.status)) {
        stop()
      } else {
        timer = setTimeout(() => poll(jobId), 700)
      }
    } catch (requestError) {
      error.value = requestError.message
      stop()
    }
  }

  function track(jobId, total = 0) {
    stop()
    error.value = ''
    job.value = { job_id: jobId, status: 'queued', done: 0, total, current_stage: '排队中' }
    startAt = Date.now()
    elapsed.value = 0
    ticker = setInterval(() => {
      elapsed.value = Math.round((Date.now() - startAt) / 1000)
    }, 1000)
    poll(jobId)
  }

  async function cancel() {
    if (!job.value?.job_id) return
    await cancelJob(job.value.job_id)
    await poll(job.value.job_id)
  }

  function reset() {
    stop()
    job.value = null
    elapsed.value = 0
    error.value = ''
  }

  onUnmounted(stop)

  return { job, status, isRunning, isSuccess, isFailed, isCancelled, progress, elapsed, error, track, cancel, reset }
}
