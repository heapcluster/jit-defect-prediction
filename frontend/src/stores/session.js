import { reactive } from 'vue'
import { fetchMe, login as loginApi, logout as logoutApi } from '../api/auth'

export const session = reactive({
  user: null,
  loaded: false,
  counts: { datasets: 0, models: 0 },
  lastLoginAt: null
})

function apply(payload) {
  session.user = payload
    ? { user_id: payload.user_id, username: payload.username, display_name: payload.display_name }
    : null
  session.counts = payload?.counts || { datasets: 0, models: 0 }
  session.lastLoginAt = payload?.last_login_at || null
}

export async function loadSession(force = false) {
  if (session.loaded && !force) return session.user
  try {
    const data = await fetchMe()
    apply(data)
  } catch (error) {
    session.user = null
  } finally {
    session.loaded = true
  }
  return session.user
}

export async function signIn(username, password) {
  const data = await loginApi(username, password)
  apply(data.user)
  session.loaded = true
  await loadSession(true)
  return session.user
}

export async function signOut() {
  try {
    await logoutApi()
  } finally {
    apply(null)
    session.loaded = true
  }
}

export function clearSession() {
  apply(null)
  session.loaded = true
}
