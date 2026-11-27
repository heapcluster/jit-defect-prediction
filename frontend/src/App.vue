<template>
  <el-container class="shell">
    <el-aside
      class="sidebar"
      width="248px"
    >
      <div class="brand">
        <span class="brand-mark">JIT</span>
        <span class="brand-copy">
          <strong>缺陷预测</strong>
          <small>Defect Intelligence</small>
        </span>
      </div>
      <el-menu
        mode="vertical"
        router
        :default-active="activeMenu"
        class="menu"
        :ellipsis="false"
      >
        <template
          v-for="group in navGroups"
          :key="group.label"
        >
          <p class="nav-group">
            {{ group.label }}
          </p>
          <el-menu-item
            v-for="item in group.items"
            :key="item.path"
            :index="item.path"
          >
            <svg
              class="nav-icon"
              viewBox="0 0 20 20"
              aria-hidden="true"
            >
              <path
                :d="item.icon"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <span class="nav-label">{{ item.label }}</span>
          </el-menu-item>
        </template>
      </el-menu>
      <div class="sidebar-footer">
        <span class="status-dot" />
        <span class="status-copy">
          <strong>本地服务</strong>
          <small>FastAPI · MySQL</small>
        </span>
      </div>
    </el-aside>

    <el-container class="workspace">
      <el-header class="topbar">
        <div class="page-header__main">
          <nav
            v-if="page.parent"
            class="breadcrumb"
            aria-label="页面层级"
          >
            <router-link :to="page.parent.path">
              {{ page.parent.title }}
            </router-link>
            <span aria-hidden="true">/</span>
            <span>{{ page.title }}</span>
          </nav>
          <div class="page-heading">
            <h1 class="page-title">
              {{ page.title }}
            </h1>
            <p
              v-if="page.subtitle"
              class="page-subtitle"
            >
              {{ page.subtitle }}
            </p>
          </div>
        </div>
        <div class="page-header__aside">
          <router-link
            v-if="page.next"
            class="next-step"
            :to="page.next.path"
          >
            <span class="next-step__label">下一步</span>
            <span>{{ page.next.label }}</span>
            <span aria-hidden="true">→</span>
          </router-link>
          <div
            v-if="page.tabs"
            id="page-header-tabs"
            class="page-header__tabs"
            aria-label="页面子视图"
          />
        </div>
      </el-header>

      <el-main class="main">
        <div class="ui-page">
          <!-- 配置读取失败时仍允许进入设置页修复，避免整站操作死锁 -->
          <router-view
            v-if="configuration.ready || route.path === '/settings'"
            v-slot="{ Component }"
          >
            <!-- 工具页切换后保留本页当前配置；刷新页面即回到空白状态，不落本地存储。 -->
            <keep-alive :include="cachedViews">
              <component :is="Component" />
            </keep-alive>
          </router-view>
          <el-alert
            v-else-if="configuration.error"
            :title="configuration.error"
            type="error"
            :closable="false"
            show-icon
          >
            <p>暂时无法加载页面设置，请重试。</p>
            <el-button
              :disabled="configuration.loading"
              @click="initializeConfiguration"
            >
              重试
            </el-button>
          </el-alert>
          <el-skeleton
            v-else
            :rows="6"
            animated
            aria-label="正在准备页面"
          />
        </div>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { configuration, loadConfiguration } from './utils/thresholds'

const route = useRoute()

// 只缓存五个工具页：来回切换时保留当前页配置；存储与设置每次进入重新读取，
// 避免新增产物或配置变更后仍看到旧数据。
const cachedViews = ['CollectTool', 'CleanTool', 'TrainTool', 'PredictTool', 'EvaluateTool']

// 功能①是系统唯一产物中心；②~⑥为工具页，⑦⑧是⑤的子页面。
// 导航按「数据 → 建模 → 系统」分组，图标使用 20×20 线性路径，避免引入图标依赖。
const navGroups = [
  {
    label: '数据',
    items: [
      { path: '/storage', label: '数据存储', icon: 'M3 5c0-1.1 3.1-2 7-2s7 .9 7 2-3.1 2-7 2-7-.9-7-2Zm0 0v5c0 1.1 3.1 2 7 2s7-.9 7-2V5M3 10v5c0 1.1 3.1 2 7 2s7-.9 7-2v-5' },
      { path: '/collect', label: '数据收集', icon: 'M6 4v9M6 8a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Zm0 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Zm8-8v2a3 3 0 0 1-3 3H9M14 7a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z' }
    ]
  },
  {
    label: '建模',
    items: [
      { path: '/clean', label: '数据清洗', icon: 'M3 5h14l-5.5 6.5V16l-3 1v-5.5L3 5Z' },
      { path: '/train', label: '模型训练', icon: 'M6 6h8v8H6V6Zm1-3v3m6-3v3m-6 8v3m6-3v3M3 7h3m-3 6h3m8-6h3m-3 6h3' },
      { path: '/predict', label: '模型预测', icon: 'M3 15l4-4 3 2 5-6M3 17h14' },
      { path: '/evaluate', label: '预测评估', icon: 'M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm0-4a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z' }
    ]
  },
  {
    label: '系统',
    items: [
      { path: '/settings', label: '系统设置', icon: 'M3 6h3m4 0h7M8 4.5v3M3 14h7m4 0h3m-3-1.5v3M3 10h7m4 0h3' }
    ]
  }
]

async function initializeConfiguration() {
  if (configuration.loading) return
  try {
    await loadConfiguration()
  } catch {
    // 错误保留在共享状态中，由布局提供可见错误及重试；绝不使用本地默认值。
  }
}

onMounted(() => {
  if (!configuration.ready) initializeConfiguration()
})

// 菜单高亮与页头信息都由路由 meta 驱动，避免在布局里堆叠路径判断。
// 数据收集的三个子签共用同一页头，不显示面包屑。
const activeMenu = computed(() => route.meta?.nav || '')
const page = computed(() => ({
  title: route.meta?.title || '',
  subtitle: route.meta?.subtitle || '',
  parent: route.meta?.parent || null,
  next: route.meta?.next || null,
  tabs: Boolean(route.meta?.tabs)
}))
</script>

<style scoped>
.shell {
  min-height: 100vh;
  background: var(--ui-bg);
}

/* ---------- 侧边导航：平色深底 + 单一强调色，不用渐变与发光 ---------- */
.sidebar {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  height: 100vh;
  flex-direction: column;
  padding: var(--ui-sidebar-padding);
  overflow: hidden;
  border-right: 1px solid var(--ui-sidebar-border);
  background: var(--ui-sidebar-bg);
  color: var(--ui-sidebar-text);
}
.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 2px 8px 0;
}
.brand-mark {
  display: inline-grid;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid var(--ui-brand-mark-border);
  border-radius: var(--ui-radius-md);
  background: var(--ui-brand-mark-bg);
  color: var(--ui-brand-mark-text);
  font-family: var(--ui-font-mono);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.brand-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
  line-height: 1.2;
}
.brand-copy strong {
  color: var(--ui-brand-title);
  font-size: 14px;
  font-weight: 650;
  letter-spacing: -0.01em;
}
.brand-copy small {
  color: var(--ui-brand-subtitle);
  font-size: 10px;
  font-family: var(--ui-font-mono);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.nav-group {
  margin: 18px 10px 4px;
  color: var(--ui-nav-group-color);
  font-size: 10px;
  font-weight: 650;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}
.nav-group:first-child {
  margin-top: 10px;
}
.menu {
  flex: 1;
  min-height: 0;
  padding-top: 2px;
  border-right: none;
  background: transparent;
  overflow-y: auto;
}
.menu :deep(.el-menu-item) {
  position: relative;
  display: flex;
  height: var(--ui-nav-height);
  align-items: center;
  gap: 10px;
  margin: 2px 0;
  padding: 0 12px 0 16px;
  border-radius: var(--ui-radius-sm);
  color: var(--ui-sidebar-text);
  font-size: var(--ui-font-base);
  font-weight: 500;
  line-height: var(--ui-nav-height);
}
.nav-icon {
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
  opacity: 0.82;
}
.nav-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.menu :deep(.el-menu-item.is-active) .nav-icon {
  opacity: 1;
}
.menu :deep(.el-menu-item:hover) {
  background: var(--p-neutral-a8);
  color: var(--ui-sidebar-text-strong);
}
.menu :deep(.el-menu-item.is-active) {
  background: var(--ui-sidebar-active-bg);
  color: var(--ui-sidebar-text-strong);
  font-weight: 600;
}
.menu :deep(.el-menu-item.is-active::before) {
  position: absolute;
  left: 6px;
  width: 2px;
  height: 18px;
  border-radius: var(--p-radius-1);
  background: var(--ui-nav-active-bar);
  content: "";
}
.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
  padding: 11px 12px;
  border: 1px solid var(--p-neutral-a10);
  border-radius: var(--ui-radius-sm);
  background: var(--p-neutral-a4);
}
.status-dot {
  width: 7px;
  height: 7px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--ui-status-dot);
}
.status-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 1px;
  line-height: 1.25;
}
.status-copy strong {
  color: var(--ui-sidebar-text-strong);
  font-size: 11px;
  font-weight: 600;
}
.status-copy small {
  color: var(--ui-sidebar-text);
  font-family: var(--ui-font-mono);
  font-size: 10px;
}

/* ---------- 内容区 ---------- */
.workspace {
  min-width: 0;
}
.topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  height: auto;
  min-height: var(--ui-topbar-height);
  align-items: center;
  justify-content: space-between;
  gap: var(--ui-space-5);
  padding: var(--ui-topbar-padding);
  border-bottom: 1px solid var(--ui-border);
  background: var(--ui-topbar-bg);
  backdrop-filter: blur(12px);
}
.page-header__main {
  min-width: 0;
}
.page-heading {
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 7px;
  color: var(--ui-text-muted);
  font-size: var(--ui-font-sm);
}
.breadcrumb a {
  color: var(--ui-primary);
  text-decoration: none;
}
.breadcrumb a:hover {
  text-decoration: underline;
}
.page-title {
  margin: 0;
  font-size: var(--ui-font-xl);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.2;
}
.page-subtitle {
  max-width: 920px;
  margin: 6px 0 0;
  color: var(--ui-text-muted);
  font-size: var(--ui-font-md);
  line-height: 1.6;
}
.page-header__aside {
  display: flex;
  flex: 0 1 auto;
  align-items: flex-end;
  gap: var(--ui-space-4);
  min-width: 0;
}
.next-step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 0;
  padding: 0 12px;
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-next-step-radius);
  background: var(--ui-surface-subtle);
  color: var(--ui-text);
  font-size: var(--ui-font-sm);
  line-height: var(--ui-next-step-height);
  font-weight: 550;
  text-decoration: none;
  white-space: nowrap;
  transition: border-color 140ms ease, color 140ms ease, background-color 140ms ease;
}
.next-step__label {
  color: var(--ui-text-muted);
  font-weight: 400;
}
.next-step:hover {
  border-color: var(--ui-primary);
  background: var(--ui-primary-soft);
  color: var(--ui-primary-hover);
}
.page-header__tabs {
  flex: 0 0 320px;
  width: 320px;
  margin-bottom: -1px;
}
.page-header__tabs:empty {
  display: none;
}
.page-header__tabs :deep(.feature-tabs) {
  min-height: 0;
  margin-bottom: 0;
}
.page-header__tabs :deep(.el-tabs__header),
.page-header__tabs :deep(.el-tabs__nav-wrap),
.page-header__tabs :deep(.el-tabs__nav),
.page-header__tabs :deep(.el-tabs__item) {
  height: var(--ui-toolbar-height);
}
.page-header__tabs :deep(.el-tabs__item) {
  line-height: var(--ui-toolbar-height);
}
.main {
  min-width: 0;
  width: 100%;
  padding: var(--ui-main-padding);
  box-sizing: border-box;
}

@media (max-width: 1100px) {
  .topbar {
    flex-direction: column;
    align-items: stretch;
    gap: var(--ui-space-3);
  }
  .page-header__aside {
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }
  .page-header__tabs {
    max-width: 100%;
  }
}

@media (max-width: 860px) {
  .shell {
    display: block;
  }
  .sidebar {
    width: 100% !important;
    height: auto;
    flex-direction: row;
    align-items: center;
    gap: 14px;
    padding: 10px 14px;
    overflow: visible;
    border-right: none;
    border-bottom: 1px solid var(--ui-sidebar-border);
  }
  .nav-group,
  .sidebar-footer {
    display: none;
  }
  .brand {
    padding: 0;
  }
  .brand-mark {
    width: 30px;
    height: 30px;
    border-radius: 8px;
  }
  .brand-copy small {
    display: none;
  }
  .menu {
    display: flex;
    height: 44px;
    flex: 1;
    min-width: 0;
    padding: 0;
    overflow-x: auto;
    overflow-y: hidden;
  }
  .menu :deep(.el-menu-item) {
    height: 38px;
    flex-shrink: 0;
    margin: 3px 2px;
    padding: 0 12px;
    border-radius: var(--ui-radius-sm);
    line-height: 38px;
    white-space: nowrap;
  }
  .menu :deep(.el-menu-item.is-active::before) {
    display: none;
  }
  .topbar {
    position: relative;
    top: auto;
    padding: 16px 18px 12px;
  }
  .main {
    padding: 18px;
  }
}

@media (max-width: 760px) {
  .topbar {
    flex-direction: column;
    align-items: stretch;
    gap: var(--ui-space-3);
  }
  .page-header__tabs {
    max-width: 100%;
  }
  .page-header__tabs :deep(.feature-tabs__nav) {
    overflow-x: auto;
  }
  .page-title {
    font-size: 22px;
  }
}
</style>
