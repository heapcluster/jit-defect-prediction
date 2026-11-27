// AI-generated navigation integration tests; not human-reviewed.
import { afterAll, afterEach, beforeAll, beforeEach, expect, it } from 'vitest'
import { config, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import App from '../src/App.vue'
import { configuration } from '../src/utils/thresholds'
import productionRouter from '../src/router'

const loadingDirective = config.global.directives.loading
beforeAll(() => { delete config.global.directives.loading })
afterAll(() => { config.global.directives.loading = loadingDirective })
let wrapper
beforeEach(() => { configuration.ready = true; configuration.error = '' })
afterEach(() => { wrapper?.unmount(); document.body.innerHTML = '' })

async function memory(path) {
  const router = createRouter({ history: createMemoryHistory(), routes: productionRouter.options.routes })
  await router.push(path); await router.isReady()
  return router
}

it('renders exactly seven ordered core-function navigation entries', async () => {
  const router = await memory('/storage')
  wrapper = mount(App, { global: { plugins: [ElementPlus, router], stubs: { RouterView: true } } })
  const items = wrapper.findAll('.menu [role="menuitem"]')
  expect(items.map(item => item.text())).toEqual(['数据存储', '数据收集', '数据清洗', '模型训练', '模型预测', '预测评估', '系统设置'])
})

it('redirects the home entry to prediction while preserving query and hash', async () => {
  const router = await memory('/?model_name=fixture_v2#kept')
  expect(router.currentRoute.value.path).toBe('/predict')
  expect(router.currentRoute.value.query).toEqual({ model_name: 'fixture_v2' })
  expect(router.currentRoute.value.hash).toBe('#kept')
})

it('keeps legacy commit URL under prediction and highlights the parent function', async () => {
  const router = await memory('/commit/' + 'a'.repeat(40) + '?model_name=fixture_v2')
  expect(router.currentRoute.value.path).toBe('/predict/commit/' + 'a'.repeat(40))
  expect(router.currentRoute.value.params.hash).toBe('a'.repeat(40))
  wrapper = mount(App, { global: { plugins: [ElementPlus, router], stubs: { RouterView: true } } })
  expect(wrapper.find('.menu .is-active').text()).toBe('模型预测')
})

it('keeps legacy model-performance and collected-datasets URLs', async () => {
  const performance = await memory('/model-performance?model_name=fixture_v2#kept')
  expect(performance.currentRoute.value.path).toBe('/evaluate/models')
  expect(performance.currentRoute.value.query).toEqual({ model_name: 'fixture_v2' })
  expect(performance.currentRoute.value.hash).toBe('#kept')
  const library = await memory('/collect/datasets?model_name=fixture_v2')
  expect(library.currentRoute.value.path).toBe('/storage')
  expect(library.currentRoute.value.query).toEqual({ model_name: 'fixture_v2', section: 'library' })
})

it('wires evaluation and model-performance routes to their real views', async () => {
  const { default: Evaluate } = await import('../src/views/Evaluate.vue')
  const { default: ModelPerformance } = await import('../src/views/ModelPerformance.vue')
  expect(productionRouter.options.routes.find(route => route.path === '/evaluate')?.component).toBe(Evaluate)
  expect(productionRouter.options.routes.find(route => route.path === '/evaluate/models')?.component).toBe(ModelPerformance)
})
