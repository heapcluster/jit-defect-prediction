import { createRouter, createWebHistory } from 'vue-router'
import PredictWorkbench from '../views/PredictWorkbench.vue'
import EvaluateWorkbench from '../views/EvaluateWorkbench.vue'
import Storage from '../views/Storage.vue'
import Collect from '../views/Collect.vue'
import Clean from '../views/Clean.vue'
import Train from '../views/Train.vue'
import Explain from '../views/Explain.vue'
import Localization from '../views/Localization.vue'

const routes = [
  { path: '/', name: 'risk-list', redirect: to => ({ path: '/predict', query: { ...to.query, section: 'risks' }, hash: to.hash }) },
  { path: '/commit/:hash', name: 'commit-detail', component: PredictWorkbench },
  { path: '/trend', name: 'trend-board', redirect: to => ({ path: '/predict', query: { ...to.query, section: 'trends' }, hash: to.hash }) },
  { path: '/model-performance', name: 'model-performance', redirect: to => ({ path: '/evaluate', query: { ...to.query, section: 'models' }, hash: to.hash }) },
  { path: '/storage', name: 'storage', component: Storage },
  { path: '/collect', name: 'collect', component: Collect },
  { path: '/clean', name: 'clean', component: Clean },
  { path: '/train', name: 'train', component: Train },
  { path: '/predict', name: 'predict', component: PredictWorkbench },
  { path: '/evaluate', name: 'evaluate', component: EvaluateWorkbench },
  { path: '/explain', name: 'explain', component: Explain },
  { path: '/localization', name: 'localization', component: Localization },
  { path: '/settings', redirect: to => ({ path: '/storage', query: { ...to.query, section: 'config' }, hash: to.hash }) },
  // 兜底路由：没有 catch-all 时，未知路径会渲染空白页（2026-10-25 修复）
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFound.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  // 路由切换后回到顶部，否则从长列表进详情再返回会停在一半的位置
  scrollBehavior() {
    return { top: 0 }
  }
})

export default router
