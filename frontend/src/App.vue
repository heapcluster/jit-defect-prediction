<template>
  <el-container class="layout">
    <el-header class="header">
      <span class="brand">JIT 缺陷预测系统</span>
      <el-menu mode="horizontal" router :default-active="$route.path" class="menu">
        <el-menu-item index="/">风险列表</el-menu-item>
        <el-menu-item index="/trend">趋势看板</el-menu-item>
      </el-menu>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
// 提交详情页不在导航里，由风险列表点击跳转进入
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
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}
</style>
