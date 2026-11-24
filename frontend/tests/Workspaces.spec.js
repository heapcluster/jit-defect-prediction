// AI-generated navigation integration tests; not human-reviewed.
import { afterAll, afterEach, beforeAll, beforeEach, expect, it } from 'vitest'
import { config, flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import ElementPlus from 'element-plus'
import App from '../src/App.vue'
import { configuration } from '../src/utils/thresholds'
import productionRouter from '../src/router'

const loaders = import.meta.glob('../src/views/*Workbench.vue')
const PredictWorkbench = loaders['../src/views/PredictWorkbench.vue'] ? (await loaders['../src/views/PredictWorkbench.vue']()).default : undefined
const EvaluateWorkbench = loaders['../src/views/EvaluateWorkbench.vue'] ? (await loaders['../src/views/EvaluateWorkbench.vue']()).default : undefined
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

it('renders exactly eight ordered core-function navigation entries', async () => {
  const router = await memory('/storage')
  wrapper = mount(App, { global: { plugins: [ElementPlus, router], stubs: { RouterView: true } } })
  const items = wrapper.findAll('.menu [role="menuitem"]')
  expect(items.map(item => item.text())).toEqual(['数据管理', '收集', '清洗', '训练', '预测', '评估', '解释', '定位及修复'])
})

it('preserves legacy risk, trend and model-performance URLs as workspace subsections', async () => {
  for (const [path, destination, section] of [['/', '/predict', 'risks'], ['/trend', '/predict', 'trends'], ['/model-performance', '/evaluate', 'models']]) {
    const router = await memory(`${path}?model_name=fixture_v2#kept`)
    expect(router.currentRoute.value.path).toBe(destination)
    expect(router.currentRoute.value.query).toEqual({ model_name: 'fixture_v2', section })
    expect(router.currentRoute.value.hash).toBe('#kept')
  }
})

it('keeps the commit URL and highlights prediction as its parent function', async () => {
  const router = await memory('/commit/' + 'a'.repeat(40) + '?model_name=fixture_v2')
  expect(router.currentRoute.value.params.hash).toBe('a'.repeat(40))
  wrapper = mount(App, { global: { plugins: [ElementPlus, router], stubs: { RouterView: true } } })
  expect(wrapper.find('.menu .is-active').text()).toBe('预测')
})

it('mounts the actual prediction, risk, trend and detail components inside one workspace', async () => {
  expect(PredictWorkbench).toBeDefined()
  const router = await memory('/predict?section=risks')
  wrapper = mount(PredictWorkbench, { global: { plugins: [ElementPlus, router], stubs: {
    Predict: { template: '<div data-testid="predict-child" />' }, RiskList: { template: '<div data-testid="risk-child" />' },
    TrendBoard: { template: '<div data-testid="trend-child" />' }, CommitDetail: { template: '<div data-testid="detail-child" />' }
  } } })
  expect(wrapper.find('[data-testid="risk-child"]').exists()).toBe(true)
  await router.push('/predict?section=trends'); await flushPromises()
  expect(wrapper.find('[data-testid="trend-child"]').exists()).toBe(true)
  await router.push('/predict'); await flushPromises()
  expect(wrapper.find('[data-testid="predict-child"]').exists()).toBe(true)
  await router.push('/commit/'+'a'.repeat(40)); await flushPromises()
  expect(wrapper.find('[data-testid="detail-child"]').exists()).toBe(true)
})

it('places existing model-performance display under the independent evaluation workspace', async () => {
  expect(EvaluateWorkbench).toBeDefined()
  const router = await memory('/evaluate?section=models')
  wrapper = mount(EvaluateWorkbench, { global: { plugins: [ElementPlus, router], stubs: {
    Evaluate: { template: '<div data-testid="evaluate-child" />' }, ModelPerformance: { template: '<div data-testid="models-child" />' }
  } } })
  expect(wrapper.find('[data-testid="models-child"]').exists()).toBe(true)
  await router.push('/evaluate'); await flushPromises()
  expect(wrapper.find('[data-testid="evaluate-child"]').exists()).toBe(true)
})
