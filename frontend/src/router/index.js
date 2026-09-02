// =====================================================================
// 前端路由（router/index.js）
// =====================================================================
// 路由 = “网址路径”和“要显示的页面组件”的对应表。点侧边栏菜单切换网址时，
// 由路由决定在 <router-view /> 位置渲染哪个 .vue 页面，且整个过程不刷新浏览器。
// =====================================================================
import { createRouter, createWebHistory } from 'vue-router'

// 路由表：每一项是一条规则
const routes = [
  { path: '/', redirect: '/overview' },   // 访问根路径时自动跳转到 /overview（总览页）
  {
    path: '/overview',                    // 网址路径
    name: 'Overview',                     // 路由名（方便编程跳转）
    component: () => import('../views/Overview.vue'),  // 懒加载：访问到才下载该页面，首屏更快
    meta: { title: '运行总览' }            // meta 放自定义信息，这里存页面标题
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

// 创建路由实例；createWebHistory 表示使用正常的网址路径（不带 # 号）
const router = createRouter({
  history: createWebHistory(),
  routes
})

// afterEach：每次成功切换页面之后执行。这里用来同步浏览器标签页标题
router.afterEach((to) => {
  // to 是即将进入的目标路由；取它 meta 里的标题拼上系统名
  document.title = `${to.meta.title || ''} - 燃气轮机排放智能优化系统`
})

export default router
