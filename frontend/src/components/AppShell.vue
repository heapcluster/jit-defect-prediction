<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">J</div>
        <div>
          <div class="brand-title">JIT 缺陷预测</div>
          <div class="brand-sub">Just-in-time defect console</div>
        </div>
      </div>

      <nav class="nav" aria-label="主导航">
        <router-link
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: isActive(item.to) }"
        >
          <span class="nav-icon" v-html="item.icon" />
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="avatar">{{ initials }}</div>
        <div class="grow">
          <div class="user-name">{{ session.user?.display_name || '未登录' }}</div>
          <div class="user-id mono">{{ session.user?.username || '—' }}</div>
        </div>
        <el-tooltip content="登出" placement="top">
          <button class="logout" aria-label="登出" @click="handleLogout">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8">
              <path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3" />
              <path d="M10 17l5-5-5-5" />
              <path d="M15 12H3" />
            </svg>
          </button>
        </el-tooltip>
      </div>
    </aside>

    <main class="main">
      <div class="main-inner">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { clearSession, session, signOut } from '../stores/session'

const route = useRoute()
const router = useRouter()

const icon = (paths) =>
  `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`

const nav = [
  { to: '/storage', label: '数据存储', icon: icon('<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>') },
  { to: '/collect', label: '数据收集', icon: icon('<circle cx="12" cy="12" r="8"/><path d="M12 8v8M8 12h8"/>') },
  { to: '/clean', label: '数据清洗', icon: icon('<path d="M4 6h16"/><path d="M7 6l1 13h8l1-13"/><path d="M10 10v6M14 10v6"/>') },
  { to: '/train', label: '模型训练', icon: icon('<path d="M4 7h10M18 7h2"/><circle cx="15" cy="7" r="2.4"/><path d="M4 17h4M12 17h8"/><circle cx="9" cy="17" r="2.4"/>') },
  { to: '/predict', label: '模型预测', icon: icon('<path d="M4 18V9M9 18V5M14 18v-6M19 18V8"/>') },
  { to: '/evaluate', label: '模型评估', icon: icon('<path d="M4 19V5"/><path d="M4 19h16"/><path d="M7 15l4-5 3 3 4-6"/>') }
]

const initials = computed(() => {
  const name = session.user?.display_name || session.user?.username || 'J'
  return name.slice(0, 1).toUpperCase()
})

function isActive(path) {
  return route.path === path || route.path.startsWith(`${path}/`)
}

async function handleLogout() {
  await signOut()
  clearSession()
  router.replace('/login')
}
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 246px minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px 18px;
  background:
    radial-gradient(420px 260px at 10% -5%, rgba(45, 212, 191, 0.24), transparent 60%),
    radial-gradient(380px 220px at 110% 30%, rgba(37, 99, 235, 0.22), transparent 60%),
    var(--surface-strong);
  color: #e2e8f0;
  overflow: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 6px 18px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.brand-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  font-weight: 800;
  font-size: 20px;
  color: #06201d;
  background: linear-gradient(135deg, #5eead4, #34d399);
  box-shadow: 0 10px 24px rgba(45, 212, 191, 0.3);
}

.brand-title {
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.02em;
  color: #f8fafc;
}

.brand-sub {
  font-size: 10.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(148, 163, 184, 0.8);
  margin-top: 3px;
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 10px 12px;
  border-radius: 11px;
  color: rgba(203, 213, 225, 0.82);
  font-weight: 550;
  font-size: 13.5px;
  transition: background 0.16s ease, color 0.16s ease, transform 0.16s ease;
  border: 1px solid transparent;
}

.nav-item:hover {
  background: rgba(148, 163, 184, 0.1);
  color: #f8fafc;
}

.nav-item.active {
  background: rgba(45, 212, 191, 0.14);
  border-color: rgba(94, 234, 212, 0.24);
  color: #d1fae5;
}

.nav-item.active .nav-icon {
  color: #5eead4;
}

.nav-icon {
  display: inline-flex;
  color: currentColor;
  opacity: 0.9;
}

.sidebar-footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 10px;
  border-radius: 12px;
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.14);
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #93c5fd, #5eead4);
  color: #0f172a;
  font-weight: 800;
}

.user-name {
  font-size: 13px;
  font-weight: 650;
  color: #f1f5f9;
}

.user-id {
  color: rgba(148, 163, 184, 0.9);
  font-size: 11px;
}

.logout {
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: transparent;
  color: #cbd5e1;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: 0.16s ease;
}

.logout:hover {
  color: #fecaca;
  border-color: rgba(248, 113, 113, 0.4);
  background: rgba(248, 113, 113, 0.1);
}

.main {
  min-width: 0;
  padding: 30px 34px 60px;
}

.main-inner {
  max-width: 1240px;
  margin: 0 auto;
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
  }

  .sidebar {
    position: static;
    height: auto;
    padding: 14px 16px;
    flex-direction: row;
    align-items: center;
    flex-wrap: wrap;
  }

  .brand {
    border-bottom: 0;
    padding: 0 12px 0 0;
  }

  .brand-sub {
    display: none;
  }

  .nav {
    flex-direction: row;
    overflow-x: auto;
    margin: 0;
    flex: 1;
    gap: 2px;
  }

  .nav-item {
    white-space: nowrap;
    padding: 8px 10px;
  }

  .sidebar-footer {
    display: none;
  }

  .main {
    padding: 20px 16px 50px;
  }
}
</style>
