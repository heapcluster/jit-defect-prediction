import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// 前端单元测试配置（2026-10-13 建立，配合 docs/common/test-strategy.md §5）
// 跑法：cd frontend && npm run test:unit
// 覆盖率：cd frontend && npm run test:coverage
export default defineConfig({
  plugins: [vue()],
  test: {
    // 只跑单元测试目录，不把 e2e / 联调脚本混进来
    include: ['src/**/__tests__/**/*.test.js'],
    environment: 'node',
    reporters: ['default']
  }
})
