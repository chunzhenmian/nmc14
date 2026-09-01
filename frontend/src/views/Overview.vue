<template>
  <div class="overview">
    <!-- 统计卡片 -->
    <el-row :gutter="16">
      <el-col :span="6" v-for="card in statCards" :key="card.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-body">
            <div class="stat-icon" :style="{ background: card.bg, color: card.color }">
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

    <!-- 设备与限值 -->
    <el-row :gutter="16" class="mt16">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><b>设备基础信息</b></template>
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
          <el-alert class="mt12" type="info" :closable="false" show-icon
            title="系统以排放达标为约束，以最大化机组能量产出为目标，提供预测、优化与预警一体化服务。" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 排放趋势 -->
    <el-card shadow="hover" class="mt16">
      <template #header><b>近期排放预测趋势</b></template>
      <div ref="trendRef" class="chart"></div>
    </el-card>

    <!-- 最近预警 -->
    <el-card shadow="hover" class="mt16">
      <template #header>
        <div class="card-header">
          <b>最近异常预警</b>
          <el-button size="small" type="primary" text @click="$router.push('/anomaly')">前往异常监测</el-button>
        </div>
      </template>
      <el-table :data="recentAnomaly" size="small" empty-text="暂无预警记录">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="level" label="预警等级" width="110">
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
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { api } from '../api'

const statCards = ref([
  { label: '排放预测次数', value: 0, icon: 'TrendCharts', bg: '#e8f3ff', color: '#4d9fff' },
  { label: '参数优化次数', value: 0, icon: 'MagicStick', bg: '#f0f9eb', color: '#67c23a' },
  { label: '异常预警记录', value: 0, icon: 'Warning', bg: '#fdf6ec', color: '#e6a23c' },
  { label: '高危预警', value: 0, icon: 'Bell', bg: '#fef0f0', color: '#f56c6c' }
])
const device = ref(null)
const emissionLimits = ref({ NOX: 100, CO: 30 })
const recentAnomaly = ref([])
const trendRef = ref(null)
let chart = null

function levelType(level) {
  return { '红色预警': 'danger', '橙色预警': 'warning', '黄色预警': 'warning', '正常': 'success' }[level] || 'info'
}

async function loadOverview() {
  try {
    const data = await api.overview()
    device.value = data.device
    emissionLimits.value = data.emission_limits || emissionLimits.value
    const s = data.stats || {}
    statCards.value[0].value = s.predict_records ?? 0
    statCards.value[1].value = s.optimize_records ?? 0
    statCards.value[2].value = s.anomaly_records ?? 0
    statCards.value[3].value = s.anomaly_high ?? 0
    recentAnomaly.value = (data.recent_anomaly || []).slice(0, 8)
    renderTrend(data.recent_predict || [])
  } catch (e) {
    console.error(e)
  }
}

function renderTrend(records) {
  if (!trendRef.value) return
  if (!chart) chart = echarts.init(trendRef.value)
  const labels = records.map((_, i) => '#' + (records.length - i))
  const nox = records.map(r => Number((r.result?.nox || 0).toFixed(1)))
  const co = records.map(r => Number((r.result?.co || 0).toFixed(2)))
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['NOX', 'CO'] },
    grid: { left: 50, right: 30, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: labels },
    yAxis: [
      { type: 'value', name: 'NOX (mg/m³)' },
      { type: 'value', name: 'CO (mg/m³)' }
    ],
    series: [
      { name: 'NOX', type: 'line', smooth: true, data: nox, itemStyle: { color: '#4d9fff' }, areaStyle: { opacity: 0.1 } },
      { name: 'CO', type: 'line', smooth: true, yAxisIndex: 1, data: co, itemStyle: { color: '#67c23a' }, areaStyle: { opacity: 0.1 } }
    ]
  })
}

onMounted(async () => {
  await nextTick()
  await loadOverview()
  window.addEventListener('resize', () => chart?.resize())
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', () => chart?.resize())
  chart?.dispose()
})
</script>

<style scoped>
.mt16 { margin-top: 16px; }
.mt12 { margin-top: 12px; }
.stat-card :deep(.el-card__body) { padding: 18px; }
.stat-body { display: flex; align-items: center; gap: 14px; }
.stat-icon { width: 52px; height: 52px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.stat-value { font-size: 24px; font-weight: 700; color: #1f2d3d; }
.stat-label { font-size: 13px; color: #8492a6; margin-top: 2px; }
.chart { height: 320px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.limit-box { background: #f6f8fb; border-radius: 8px; padding: 14px 18px; }
.limit-label { font-size: 13px; color: #8492a6; }
.limit-value { font-size: 24px; font-weight: 700; color: #f56c6c; }
.limit-value span { font-size: 13px; font-weight: 400; color: #8492a6; }
</style>
