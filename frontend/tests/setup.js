// jsdom 环境下的通用测试初始化。
// 每个用例结束后清理挂载到 body 的节点，避免组件之间的样式与事件残留。
import { afterEach } from 'vitest'

afterEach(() => {
  document.body.innerHTML = ''
})
