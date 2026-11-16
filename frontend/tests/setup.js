// Element Plus 挂载依赖的浏览器 API，jsdom 未实现，补最小桩避免测试报错
import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// v-loading 由 Element Plus 插件注册；单测不挂完整插件，注册一个 noop 指令避免 Vue warn 噪声
config.global.directives.loading = {}

if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}

if (!globalThis.matchMedia) {
  globalThis.matchMedia = vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
}
