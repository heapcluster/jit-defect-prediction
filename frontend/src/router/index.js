import { createRouter, createWebHistory } from 'vue-router'
import RiskList from '../views/RiskList.vue'
import CommitDetail from '../views/CommitDetail.vue'
import TrendBoard from '../views/TrendBoard.vue'

const routes = [
  { path: '/', name: 'risk-list', component: RiskList },
  // 详情页带 commit_hash，从风险列表点击跳转
  { path: '/commit/:hash', name: 'commit-detail', component: CommitDetail, props: true },
  { path: '/trend', name: 'trend-board', component: TrendBoard }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
