import { createRouter, createWebHistory } from 'vue-router'
import Collect from '../views/Collect.vue'
import Clean from '../views/Clean.vue'
import Train from '../views/Train.vue'
import Predict from '../views/Predict.vue'
import Evaluate from '../views/Evaluate.vue'
import Settings from '../views/Settings.vue'
import Storage from '../views/Storage.vue'
import CommitDetail from '../views/CommitDetail.vue'
import ModelPerformance from '../views/ModelPerformance.vue'

// 页面标题、说明与所属顶级导航统一由 meta 描述：
// nav 决定顶级菜单高亮，parent 生成「功能 / 子页面」面包屑。
// 结果解释与定位及修复已收敛到提交详情页内联展示，不再单独成页。
const predictMeta = {
  nav: '/predict',
  title: '模型预测',
  subtitle: '加载模型与待预测数据，产出风险结果，并可继续解释原因、定位可疑代码',
  next: { path: '/evaluate', label: '预测评估' }
}

const routes = [
  { path: '/', name: 'home', redirect: to => ({ path: '/predict', query: to.query, hash: to.hash }) },
  {
    path: '/storage',
    name: 'storage',
    component: Storage,
    meta: {
      nav: '/storage',
      title: '数据存储',
      subtitle: '查看、选择、下载与删除系统产物，导入外部文件到产物库',
      tabs: true
    }
  },
  { path: '/collect', name: 'collect', component: Collect, meta: { nav: '/collect', title: '数据收集', subtitle: '从 Git 仓库或公开数据集 URL 采集标注提交，并保存到数据集库', next: { path: '/clean', label: '数据清洗' } } },
  // 旧地址兼容：已收集数据已并入 /storage 产物库
  { path: '/collect/datasets', redirect: to => ({ path: '/storage', query: { ...to.query, section: 'library' }, hash: to.hash }) },
  { path: '/clean', name: 'clean', component: Clean, meta: { nav: '/clean', title: '数据清洗', subtitle: '按处理项清洗数据，并对比每一步的变化', next: { path: '/train', label: '模型训练' } } },
  { path: '/train', name: 'train', component: Train, meta: { nav: '/train', title: '模型训练', subtitle: '划分数据集，训练并对比一个或多个算法', next: { path: '/predict', label: '模型预测' } } },
  { path: '/predict', name: 'predict', component: Predict, meta: predictMeta },
  {
    path: '/predict/commit/:hash',
    name: 'commit-detail',
    component: CommitDetail,
    props: true,
    meta: { nav: '/predict', parent: { path: '/predict', title: '模型预测' }, title: '提交详情', subtitle: '单次提交的风险、解释与定位结果' }
  },
  { path: '/evaluate', name: 'evaluate', component: Evaluate, meta: { nav: '/evaluate', title: '预测评估', subtitle: '按指标评估预测质量，并查看模型性能记录' } },
  { path: '/evaluate/models', name: 'model-performance', component: ModelPerformance, meta: { nav: '/evaluate', parent: { path: '/evaluate', title: '预测评估' }, title: '模型性能', subtitle: '查看已登记模型的历史性能记录' } },
  { path: '/settings', name: 'settings', component: Settings, meta: { nav: '/settings', title: '系统设置', subtitle: '调整风险分档阈值，保存后立即在所有页面生效' } },
  // 兼容旧入口：旧的提交详情与模型性能地址仍可访问
  { path: '/model-performance', name: 'legacy-model-performance', redirect: to => ({ path: '/evaluate/models', query: to.query, hash: to.hash }) },
  { path: '/commit/:hash', name: 'legacy-commit-detail', redirect: to => ({ path: '/predict/commit/' + to.params.hash, query: to.query, hash: to.hash }) },
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

// 旧来源子签合并为单一收集页，来源改由 source query 记录。
router.beforeEach(to => {
  if (to.path === '/collect' && (to.query.section === 'git' || to.query.section === 'public')) {
    const { section, ...query } = to.query
    if (section === 'public') query.source = 'public'
    return { path: '/collect', query, hash: to.hash, replace: true }
  }
  return true
})

export default router
