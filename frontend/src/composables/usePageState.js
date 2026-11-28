import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { deletePageState, getPageState, putPageState } from '../api/pageState'

export function usePageState(page, factory) {
  const state = reactive(factory())
  const loaded = ref(false)
  const syncError = ref('')
  let timer = null
  let skip = true
  let resolveReady
  const ready = new Promise((resolve) => {
    resolveReady = resolve
  })

  async function restore() {
    try {
      const data = await getPageState(page)
      if (data?.state) {
        Object.assign(state, factory(), data.state)
      }
    } catch (error) {
      syncError.value = error.message
    } finally {
      loaded.value = true
      skip = false
      if (resolveReady) {
        resolveReady()
        resolveReady = null
      }
    }
  }

  function snapshot() {
    return JSON.parse(JSON.stringify(state))
  }

  async function save() {
    try {
      await putPageState(page, snapshot())
      syncError.value = ''
    } catch (error) {
      syncError.value = error.message
    }
  }

  function schedule() {
    if (timer) clearTimeout(timer)
    timer = setTimeout(save, 500)
  }

  async function reset() {
    if (timer) clearTimeout(timer)
    try {
      await deletePageState(page)
    } finally {
      Object.assign(state, factory())
      skip = true
      loaded.value = true
      setTimeout(() => {
        skip = false
      }, 0)
    }
  }

  watch(
    state,
    () => {
      if (!skip && loaded.value) schedule()
    },
    { deep: true }
  )

  onMounted(restore)
  onUnmounted(() => {
    if (timer) clearTimeout(timer)
  })

  return { state, loaded, ready, syncError, restore, save, reset }
}
