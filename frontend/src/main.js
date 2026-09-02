// =====================================================================
// 前端总入口（main.js）
// =====================================================================
// 浏览器打开系统后，第一个执行的就是这个文件：创建 Vue 应用、装好界面组件库、
// 挂上路由，最后把整个应用渲染到 index.html 里 id="app" 的位置。
// =====================================================================
import { createApp } from 'vue'                 // Vue3 的创建应用函数
import ElementPlus from 'element-plus'          // Element Plus：现成的 UI 组件库（按钮、表格、菜单等）
import 'element-plus/dist/index.css'            // 组件库的样式表，必须引入
import zhCn from 'element-plus/es/locale/lang/zh-cn'  // 组件库中文语言包（让分页等显示中文）
import * as ElementPlusIconsVue from '@element-plus/icons-vue' // 全部图标
import App from './App.vue'                     // 根组件（整体页面骨架）
import router from './router'                   // 路由：决定不同网址显示哪个页面

const app = createApp(App)                       // 以 App.vue 为根创建应用实例

// 把所有 Element 图标逐个注册成“全局组件”，之后在任何页面直接写图标名就能用
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus, { locale: zhCn })          // 启用组件库并设置为中文
app.use(router)                                  // 启用路由
app.mount('#app')                                // 挂载到页面中 id=app 的 DOM 节点
