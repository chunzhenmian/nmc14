<!--
  =====================================================================
  根组件 App.vue：整个系统的“外壳/布局骨架”
  =====================================================================
  一个 .vue 文件分三块：
    <template> 页面结构（HTML）
    <script setup> 交互逻辑（JavaScript）
    <style> 样式（CSS）
  本组件负责左侧导航菜单 + 顶部标题栏，中间 <router-view /> 用来显示当前页面。
-->
<template>
  <!-- el-container 是 Element 的布局容器，整体左右排列 -->
  <el-container class="layout">
    <!-- ============ 侧边栏（固定 220px 宽） ============ -->
    <el-aside width="220px" class="aside">
      <!-- 左上角 Logo 与系统名 -->
      <div class="logo">
        <el-icon :size="26"><Monitor /></el-icon>
        <div class="logo-text">
          <div class="logo-title">燃气轮机排放</div>
          <div class="logo-sub">智能优化系统</div>
        </div>
      </div>
      <!-- 导航菜单：
           :default-active="$route.path" 让当前网址对应的菜单项高亮；
           router 属性表示点击菜单项直接按 index 路径跳转 -->
      <el-menu
        :default-active="$route.path"
        router
        class="menu"
        background-color="#0f1b2d"
        text-color="#a3b1c6"
        active-text-color="#4d9fff"
      >
        <!-- index 就是点击后跳转的路径，与路由表一一对应 -->
        <el-menu-item index="/overview">
          <el-icon><Odometer /></el-icon>
          <span>运行总览</span>
        </el-menu-item>
        <el-menu-item index="/prediction">
          <el-icon><TrendCharts /></el-icon>
          <span>排放预测</span>
        </el-menu-item>
        <el-menu-item index="/optimization">
          <el-icon><MagicStick /></el-icon>
          <span>参数优化</span>
        </el-menu-item>
        <el-menu-item index="/anomaly">
          <el-icon><Warning /></el-icon>
          <span>异常监测</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 右侧：上下排列（顶栏 + 内容区） -->
    <el-container>
      <!-- ============ 顶部标题栏 ============ -->
      <el-header class="header">
        <!-- 左侧显示当前页面标题（来自 script 里的 currentTitle） -->
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-right">
          <!-- 右上角状态标签 -->
          <el-tag type="success" effect="dark" size="small">系统运行正常</el-tag>
          <span class="sys-name">工业燃气轮机排放预测与运行参数智能优化系统</span>
        </div>
      </el-header>

      <!-- ============ 内容区：路由匹配到的页面会渲染在这里 ============ -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
// Vue 3 的组合式 API 写法（setup 语法糖）
import { computed } from 'vue'      // computed：定义“会随数据自动变化”的计算值
import { useRoute } from 'vue-router' // useRoute：拿到当前路由信息（路径、meta 等）

const route = useRoute()
// 当前页面标题：随路由变化自动更新，template 里用 {{ currentTitle }} 显示
const currentTitle = computed(() => route.meta.title || '')
</script>

<style>
/* 全局基础样式：* 通配所有元素，先清掉浏览器默认外边距/内边距，border-box 让宽高计算更直观 */
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }   /* 让根节点占满整屏高度 */
body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f0f2f5; }

.layout { height: 100vh; }           /* 整个布局占满一屏（vh=视口高度百分比） */
.aside { background: #0f1b2d; }      /* 侧边栏深蓝背景 */
/* Logo 区：flex 横向排列、垂直居中、元素间距 10px */
.logo {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 16px; color: #fff; border-bottom: 1px solid rgba(255,255,255,.08);
}
.logo-text .logo-title { font-size: 15px; font-weight: 600; }
.logo-text .logo-sub { font-size: 11px; color: #7a8aa0; }
.menu { border-right: none; }        /* 去掉菜单右侧默认边框 */
/* 顶栏：白底、左右两端对齐、轻微阴影营造层次 */
.header {
  background: #fff; display: flex; align-items: center; justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0,21,41,.08); z-index: 1;
}
.header-title { font-size: 17px; font-weight: 600; color: #1f2d3d; }
.header-right { display: flex; align-items: center; gap: 12px; }
.sys-name { font-size: 12px; color: #8492a6; }
.main { padding: 18px; overflow: auto; }  /* 内容区内边距，内容过多时自身滚动 */
</style>
