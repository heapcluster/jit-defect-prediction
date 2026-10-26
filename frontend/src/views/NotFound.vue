<template>
  <div>
    <h2>页面不存在</h2>
    <p>该地址没有对应页面，请从顶部导航进入。</p>
    <el-button
      type="primary"
      @click="$router.push('/')"
    >
      回到风险列表
    </el-button>
  </div>
</template>

<script setup>
</script>
