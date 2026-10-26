<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="brand">JIT 缺陷预测系统</span>
      <el-menu
        mode="horizontal"
        router
        :default-active="activeMenu"
        class="menu"
      >
        <el-menu-item index="/">
          风险列表
        </el-menu-item>
        <el-menu-item index="/prs">
          PR 列表
        </el-menu-item>
        <el-menu-item index="/trend">
          趋势看板
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
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

// 提交详情页不在导航里，由风险列表点击跳转进入

// 菜单高亮：default-active 只在首次渲染生效，路由变化后要跟着更新；
// 详情页（/commit/:hash、/prs/:number）归到它所属的列表项
const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/prs')) return '/prs'
  if (path.startsWith('/trend')) return '/trend'
  return '/'
})

// 页头标题由布局统一提供，页面内不再重复写 h2（2026-10-26 去重）
const pageTitle = computed(() => {
  const path = route.path
  if (path.startsWith('/prs/')) return 'PR 详情'
  if (path.startsWith('/prs')) return 'PR 列表'
  if (path.startsWith('/commit/')) return '提交详情'
  if (path.startsWith('/trend')) return '缺陷引入趋势'
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
  border-bottom: none;
}
.main {
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
</style>
