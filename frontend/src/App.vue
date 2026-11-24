<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="brand">JIT 缺陷预测</span>
      <el-menu
        mode="horizontal"
        router
        :default-active="activeMenu"
        class="menu"
        :ellipsis="false"
      >
        <el-menu-item index="/storage">
          数据管理
        </el-menu-item>
        <el-menu-item index="/collect">
          收集
        </el-menu-item>
        <el-menu-item index="/clean">
          清洗
        </el-menu-item>
        <el-menu-item index="/train">
          训练
        </el-menu-item>
        <el-menu-item index="/predict">
          预测
        </el-menu-item>
        <el-menu-item index="/evaluate">
          评估
        </el-menu-item>
        <el-menu-item index="/explain">
          解释
        </el-menu-item>
        <el-menu-item index="/localization">
          定位及修复
        </el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="main">
      <h1
        v-if="pageTitle"
        class="page-title"
      >
        {{ pageTitle }}
      </h1>
      <router-view v-if="configuration.ready" />
      <el-alert
        v-else-if="configuration.error"
        :title="configuration.error"
        type="error"
        :closable="false"
        show-icon
      >
        <p>运行配置尚未读取，业务页面暂不可用。</p>
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
        aria-label="正在读取运行配置"
      />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { configuration, loadConfiguration } from './utils/thresholds'

const route = useRoute()

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

// 菜单高亮：default-active 只在首次渲染生效，路由变化后要跟着更新；
// 详情页（/commit/:hash）归到预测功能项
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/commit/')) return '/predict'
  if (path === '/storage' || path === '/settings') return '/storage'
  if (path === '/collect') return '/collect'
  if (path === '/clean') return '/clean'
  if (path === '/train') return '/train'
  if (path === '/predict') return '/predict'
  if (path === '/evaluate') return '/evaluate'
  if (path === '/explain') return '/explain'
  if (path === '/localization') return '/localization'
  return ''
})

// 页头标题由布局统一提供，页面内不再重复写 h2
const pageTitle = computed(() => {
  const path = route.path
  if (path.startsWith('/commit/')) return '提交详情'
  if (path.startsWith('/trend')) return '缺陷引入趋势'
  if (path.startsWith('/model-performance')) return '模型性能看板'
  if (path === '/storage' || path === '/settings') return '数据管理'
  if (path === '/collect') return '缺陷数据收集'
  if (path === '/clean') return '数据清洗与预处理'
  if (path === '/train') return '模型训练'
  if (path === '/predict') return '模型预测'
  if (path === '/evaluate') return '预测性能评估'
  if (path === '/explain') return '预测结果解释'
  if (path === '/localization') return '定位及修复'
  if (path === '/') return '风险列表'
  // 未知路径交给 404 页自己说明，布局层不再冒出一个不相干的标题
  return ''
})
</script>

<style scoped>
.layout {
  min-height: 100vh;
}
.header {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 24px;
  border-bottom: 1px solid var(--el-border-color-light);
}
.brand {
  font-weight: 600;
  font-size: 16px;
}
.menu {
  flex: 1;
  min-width: 0;
  border-bottom: none;
}
.main {
  min-width: 0;
  width: 100%;
  padding: 18px 24px 24px;
  box-sizing: border-box;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
@media (max-width: 640px) {
  .header {
    height: auto;
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    padding: 12px 16px 0;
  }
  .menu {
    width: 100%;
    overflow-x: auto;
  }
  .main {
    padding: 16px;
  }
}
</style>
