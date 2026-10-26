import { createRouter, createWebHistory } from 'vue-router'
import RiskList from '../views/RiskList.vue'
import CommitDetail from '../views/CommitDetail.vue'
import TrendBoard from '../views/TrendBoard.vue'
import PrList from '../views/PrList.vue'
import PrDetail from '../views/PrDetail.vue'

const routes = [
  { path: '/', name: 'risk-list', component: RiskList },
  // 详情页带 commit_hash，从风险列表点击跳转
  { path: '/commit/:hash', name: 'commit-detail', component: CommitDetail, props: true },
  { path: '/trend', name: 'trend-board', component: TrendBoard },
  { path: '/prs', name: 'pr-list', component: PrList },
  { path: '/prs/:number', name: 'pr-detail', component: PrDetail, props: true },
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
