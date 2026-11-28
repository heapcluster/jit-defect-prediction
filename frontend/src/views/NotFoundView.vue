<template>
  <div class="not-found">
    <div class="code">404</div>
    <h1>页面不存在</h1>
    <p>地址可能已失效，或该能力不在当前设计范围内。</p>
    <el-button type="primary" @click="$router.replace('/storage')">回到数据存储</el-button>
  </div>
</template>

<style scoped>
.not-found {
  min-height: 60vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  text-align: center;
}

.code {
  font-family: var(--mono);
  font-size: 64px;
  font-weight: 800;
  color: var(--primary);
  letter-spacing: -0.05em;
}

h1 {
  font-size: 22px;
}

p {
  color: var(--text-muted);
  margin-bottom: 8px;
}
</style>
