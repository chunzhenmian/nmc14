<template>
  <el-container class="layout">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="aside">
      <div class="logo">
        <el-icon :size="26"><Monitor /></el-icon>
        <div class="logo-text">
          <div class="logo-title">燃气轮机排放</div>
          <div class="logo-sub">智能优化系统</div>
        </div>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="menu"
        background-color="#0f1b2d"
        text-color="#a3b1c6"
        active-text-color="#4d9fff"
      >
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

    <el-container>
      <!-- 顶栏 -->
      <el-header class="header">
        <div class="header-title">{{ currentTitle }}</div>
        <div class="header-right">
          <el-tag type="success" effect="dark" size="small">系统运行正常</el-tag>
          <span class="sys-name">工业燃气轮机排放预测与运行参数智能优化系统</span>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentTitle = computed(() => route.meta.title || '')
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; }
body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #f0f2f5; }

.layout { height: 100vh; }
.aside { background: #0f1b2d; }
.logo {
  display: flex; align-items: center; gap: 10px;
  padding: 18px 16px; color: #fff; border-bottom: 1px solid rgba(255,255,255,.08);
}
.logo-text .logo-title { font-size: 15px; font-weight: 600; }
.logo-text .logo-sub { font-size: 11px; color: #7a8aa0; }
.menu { border-right: none; }
.header {
  background: #fff; display: flex; align-items: center; justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0,21,41,.08); z-index: 1;
}
.header-title { font-size: 17px; font-weight: 600; color: #1f2d3d; }
.header-right { display: flex; align-items: center; gap: 12px; }
.sys-name { font-size: 12px; color: #8492a6; }
.main { padding: 18px; overflow: auto; }
</style>
