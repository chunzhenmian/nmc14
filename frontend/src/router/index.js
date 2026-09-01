import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/overview' },
  {
    path: '/overview',
    name: 'Overview',
    component: () => import('../views/Overview.vue'),
    meta: { title: '运行总览' }
  },
  {
    path: '/prediction',
    name: 'Prediction',
    component: () => import('../views/Prediction.vue'),
    meta: { title: '排放预测' }
  },
  {
    path: '/optimization',
    name: 'Optimization',
    component: () => import('../views/Optimization.vue'),
    meta: { title: '参数优化' }
  },
  {
    path: '/anomaly',
    name: 'AnomalyMonitor',
    component: () => import('../views/AnomalyMonitor.vue'),
    meta: { title: '异常监测' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach((to) => {
  document.title = `${to.meta.title || ''} - 燃气轮机排放智能优化系统`
})

export default router
