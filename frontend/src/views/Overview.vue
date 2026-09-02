<!--
  =====================================================================
  页面：运行总览（Overview.vue）
  =====================================================================
  进入系统默认看到的首页：顶部 4 张统计卡片、设备信息与排放限值、
  近期排放预测趋势折线图（ECharts）、最近异常预警表格。
  数据都来自后端 GET /api/overview，页面加载时请求一次。
-->
<template>
  <div class="overview">
    <!-- ===== 顶部 4 张统计卡片：用 v-for 遍历 statCards 数组自动生成 ===== -->
    <el-row :gutter="16">
      <!-- :span="6" 表示每张卡占 24 栅格中的 6 份，正好 4 张排满一行 -->
      <el-col :span="6" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-body">
            <!-- 左侧圆形图标，背景色/图标色由每张卡的数据决定（:style 动态绑定） -->
            <div class="stat-icon" :style="{ background: card.bg, color: card.color }">
              <!-- <component :is> 动态渲染名字存在 card.icon 里的图标组件 -->
              <el-icon :size="26"><component :is="card.icon" /></el-icon>
            </div>
            <div>
              <div class="stat-value">{{ card.value }}</div>
              <div class="stat-label">{{ card.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 设备信息 + 排放限值 ===== -->
    <el-row :gutter="16" class="mt16">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><b>设备基础信息</b></template>
          <!-- v-if="device"：有设备数据才显示描述列表，否则显示“暂无数据” -->
          <el-descriptions :column="1" size="small" v-if="device">
            <el-descriptions-item label="设备名称">{{ device.device_name }}</el-descriptions-item>
            <el-descriptions-item label="额定功率">{{ device.rated_power_mw }} MW</el-descriptions-item>
            <el-descriptions-item label="设计涡轮进口温度">{{ device.design_tit_c }} °C</el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="暂无设备数据" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><b>排放达标限值</b></template>
          <el-row :gutter="12">
            <el-col :span="12">
              <div class="limit-box">
                <div class="limit-label">NOX 排放限值</div>
                <!-- {{ }} 是 Vue 插值语法，把变量值显示到页面 -->
                <div class="limit-value">{{ emissionLimits.NOX }} <span>mg/m³</span></div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="limit-box">
                <div class="limit-label">CO 排放限值</div>
                <div class="limit-value">{{ emissionLimits.CO }} <span>mg/m³</span></div>
              </div>
            </el-col>
          </el-row>
          <!-- 提示条：closable=false 不显示关闭按钮，show-icon 显示左侧图标 -->
          <el-alert class="mt12" type="info" :closable="false" show-icon
            title="系统以排放达标为约束，以最大化机组能量产出为目标，提供预测、优化与预警一体化服务。" />
        </el-card>
      </el-col>
    </el-row>

    <!-- ===== 近期排放预测趋势图：图由 ECharts 画在这个 div 里（ref 用于在 JS 中拿到它） ===== -->
    <el-card shadow="hover" class="mt16">
      <template #header><b>近期排放预测趋势</b></template>
      <div ref="trendRef" class="chart"></div>
    </el-card>

    <!-- ===== 最近异常预警表格 ===== -->
    <el-card shadow="hover" class="mt16">
      <template #header>
        <div class="card-header">
          <b>最近异常预警</b>
          <!-- 点击按钮用 $router.push 编程式跳转到异常监测页 -->
          <el-button size="small" type="primary" text @click="$router.push('/anomaly')">前往异常监测</el-button>
        </div>
      </template>
      <!-- :data 绑定表格数据源；empty-text 是无数据时的提示 -->
      <el-table :data="recentAnomaly" size="small" empty-text="暂无预警记录">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="level" label="预警等级" width="110">
          <!-- 用作用域插槽自定义这一列：等级用不同颜色的标签显示 -->
          <template #default="{ row }">
            <el-tag :type="levelType(row.level)" effect="dark">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="260" />
        <el-table-column prop="created_at" label="时间" width="180" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
// ref：定义响应式数据（值变化时页面自动更新）；
// onMounted：组件挂载到页面后执行；onBeforeUnmount：组件离开前执行（做清理）；
// nextTick：等 DOM 更新完成后再执行回调。
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'   // ECharts 图表库
import { api } from '../api'          // 后端接口封装

// 4 张统计卡片的初始数据（value 初始 0，请求后端后更新）
const statCards = ref([
  { label: '排放预测次数', value: 0, icon: 'TrendCharts', bg: '#e8f3ff', color: '#4d9fff' },
  { label: '参数优化次数', value: 0, icon: 'MagicStick', bg: '#f0f9eb', color: '#67c23a' },
  { label: '异常预警记录', value: 0, icon: 'Warning', bg: '#fdf6ec', color: '#e6a23c' },
  { label: '高危预警', value: 0, icon: 'Bell', bg: '#fef0f0', color: '#f56c6c' }
])
const device = ref(null)                          // 设备信息，初始为空
const emissionLimits = ref({ NOX: 100, CO: 30 })  // 排放限值（先给默认值，后端返回后覆盖）
const recentAnomaly = ref([])                     // 最近异常列表
const trendRef = ref(null)                        // 趋势图 div 的引用
let chart = null                                  // ECharts 实例（非响应式，用普通变量）

// 把预警等级文字映射成 Element 标签的颜色类型
function levelType(level) {
  return { '红色预警': 'danger', '橙色预警': 'warning', '黄色预警': 'warning', '正常': 'success' }[level] || 'info'
}

// 请求总览数据并填充到页面（async/await：异步请求，等待结果返回再继续）
async function loadOverview() {
  try {
    const data = await api.overview()   // 调后端总览接口
    device.value = data.device
    emissionLimits.value = data.emission_limits || emissionLimits.value
    const s = data.stats || {}
    // ?? 是空值合并运算符：左边为 null/undefined 时用右边的 0
    statCards.value[0].value = s.predict_records ?? 0
    statCards.value[1].value = s.optimize_records ?? 0
    statCards.value[2].value = s.anomaly_records ?? 0
    statCards.value[3].value = s.anomaly_high ?? 0
    recentAnomaly.value = (data.recent_anomaly || []).slice(0, 8)  // 最多显示 8 条
    renderTrend(data.recent_predict || [])                        // 用最近预测记录画趋势图
  } catch (e) {
    console.error(e)   // 请求失败只在控制台打印，不影响页面其它部分
  }
}

// 用最近预测记录画 NOX/CO 双纵轴折线图
function renderTrend(records) {
  if (!trendRef.value) return
  if (!chart) chart = echarts.init(trendRef.value)   // 图实例只初始化一次
  // 横轴标签：按记录倒序编号 #n、#n-1 ...
  const labels = records.map((_, i) => '#' + (records.length - i))
  // r.result?.nox：可选链取嵌套字段；toFixed(1) 保留 1 位小数；Number 再转回数字
  const nox = records.map(r => Number((r.result?.nox || 0).toFixed(1)))
  const co = records.map(r => Number((r.result?.co || 0).toFixed(2)))
  chart.setOption({
    tooltip: { trigger: 'axis' },        // 鼠标悬停显示该点数值
    legend: { data: ['NOX', 'CO'] },     // 图例
    grid: { left: 50, right: 30, top: 40, bottom: 30 },  // 图距容器四边的距离
    xAxis: { type: 'category', data: labels },            // 横轴：类别轴（编号）
    yAxis: [
      { type: 'value', name: 'NOX (mg/m³)' },   // 左纵轴给 NOX
      { type: 'value', name: 'CO (mg/m³)' }     // 右纵轴给 CO（两者数值量级不同）
    ],
    series: [
      // NOX 用左轴，蓝色折线 + 浅色面积
      { name: 'NOX', type: 'line', smooth: true, data: nox, itemStyle: { color: '#4d9fff' }, areaStyle: { opacity: 0.1 } },
      // yAxisIndex:1 指定 CO 用第二个（右）纵轴，绿色
      { name: 'CO', type: 'line', smooth: true, yAxisIndex: 1, data: co, itemStyle: { color: '#67c23a' }, areaStyle: { opacity: 0.1 } }
    ]
  })
}

// 组件挂载后：等 DOM 就绪 → 加载数据 → 监听窗口大小变化让图自适应
onMounted(async () => {
  await nextTick()
  await loadOverview()
  window.addEventListener('resize', () => chart?.resize())
})
// 组件离开前：移除监听并销毁图表，释放内存、避免内存泄漏
onBeforeUnmount(() => {
  window.removeEventListener('resize', () => chart?.resize())
  chart?.dispose()
})
</script>

<!-- scoped：这些样式只在当前组件内生效，不会污染其它页面 -->
<style scoped>
.mt16 { margin-top: 16px; }
.mt12 { margin-top: 12px; }
/* :deep() 穿透到 Element 组件内部，调整卡片内边距 */
.stat-card :deep(.el-card__body) { padding: 18px; }
.stat-body { display: flex; align-items: center; gap: 14px; }
.stat-icon { width: 52px; height: 52px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.stat-value { font-size: 24px; font-weight: 700; color: #1f2d3d; }
.stat-label { font-size: 13px; color: #8492a6; margin-top: 2px; }
.chart { height: 320px; }   /* 图表必须给高度，否则 ECharts 画不出来 */
.card-header { display: flex; justify-content: space-between; align-items: center; }
.limit-box { background: #f6f8fb; border-radius: 8px; padding: 14px 18px; }
.limit-label { font-size: 13px; color: #8492a6; }
.limit-value { font-size: 24px; font-weight: 700; color: #f56c6c; }
.limit-value span { font-size: 13px; font-weight: 400; color: #8492a6; }
</style>
