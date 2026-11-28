import { createRouter, createWebHistory } from 'vue-router'
import { loadSession, session } from '../stores/session'
import { setUnauthorizedHandler } from '../api/http'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true, title: '登录' }
  },
  {
    path: '/',
    component: () => import('../components/AppShell.vue'),
    children: [
      { path: '', redirect: '/storage' },
      { path: 'storage', name: 'storage', component: () => import('../views/StorageView.vue'), meta: { title: '数据存储' } },
      { path: 'collect', name: 'collect', component: () => import('../views/CollectView.vue'), meta: { title: '数据收集' } },
      { path: 'clean', name: 'clean', component: () => import('../views/CleanView.vue'), meta: { title: '数据清洗' } },
      { path: 'train', name: 'train', component: () => import('../views/TrainView.vue'), meta: { title: '模型训练' } },
      { path: 'predict', name: 'predict', component: () => import('../views/PredictView.vue'), meta: { title: '模型预测' } },
      {
        path: 'predict/:jobId/commit/:commitHash',
        name: 'predict-detail',
        component: () => import('../views/PredictDetailView.vue'),
        meta: { title: '预测详情' }
      },
      { path: 'evaluate', name: 'evaluate', component: () => import('../views/EvaluateView.vue'), meta: { title: '模型评估' } },
      { path: 'settings', redirect: '/storage?section=config' }
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue'), meta: { public: true } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach(async (to) => {
  const user = await loadSession()
  if (to.meta.public) {
    if (to.path === '/login' && user) return '/storage'
    return true
  }
  if (!user) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · JIT 缺陷预测` : 'JIT 缺陷预测'
})

setUnauthorizedHandler(() => {
  if (session.user) {
    session.user = null
    session.loaded = true
  }
  const current = router.currentRoute.value
  if (current.path !== '/login') {
    router.replace({ path: '/login', query: { redirect: current.fullPath } })
  }
})

export default router
