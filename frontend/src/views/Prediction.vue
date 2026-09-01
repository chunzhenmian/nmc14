<template>
  <div class="prediction">
    <el-row :gutter="16">
      <!-- 参数输入 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <b>运行参数输入</b>
              <div>
                <el-button size="small" @click="fillTypical">填入典型工况</el-button>
                <el-button size="small" type="primary" :loading="loading" @click="doPredict">开始预测</el-button>
              </div>
            </div>
          </template>
          <el-form label-width="120px" size="default">
            <el-form-item v-for="f in paramFields" :key="f.key" :label="f.label">
              <el-input-number
                v-model="params[f.key]"
                :min="f.min" :max="f.max" :step="f.step" :precision="f.precision"
                controls-position="right" style="width: 100%"
              />
              <div class="field-hint">{{ f.unit }}</div>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 预测结果 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header><b>预测结果</b></template>
          <el-empty v-if="!result" description="输入运行参数后点击「开始预测」" />
          <template v-else>
            <el-row :gutter="12">
              <el-col :span="8" v-for="m in metricCards" :key="m.key">
                <div class="metric" :style="{ borderTop: '3px solid ' + m.color }">
                  <div class="metric-label">{{ m.label }}</div>
                  <div class="metric-value" :style="{ color: m.color }">{{ result[m.key]?.toFixed(2) }}</div>
                  <div class="metric-unit">{{ m.unit }}</div>
                </div>
              </el-col>
            </el-row>

            <el-row :gutter="12" class="mt16">
              <el-col :span="12">
                <el-card shadow="never" class="grade-box">
                  <div class="grade-label">综合排放等级</div>
                  <el-tag :type="gradeType(result.grade.overall)" size="large" effect="dark" class="grade-tag">
                    {{ result.grade.overall }}
                  </el-tag>
                  <div class="grade-sub">
                    CO：{{ result.grade.co_grade }} / NOX：{{ result.grade.nox_grade }}
                  </div>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card shadow="never" class="grade-box">
                  <div class="grade-label">达标判定</div>
                  <el-tag :type="result.standards_met ? 'success' : 'danger'" size="large" effect="dark" class="grade-tag">
                    {{ result.standards_met ? '排放达标' : '排放超标' }}
                  </el-tag>
                  <div class="grade-sub">限值：NOX ≤ {{ result.grade.nox_limit }}，CO ≤ {{ result.grade.co_limit }} mg/m³</div>
                </el-card>
              </el-col>
            </el-row>

            <!-- 排放对比图 -->
            <div ref="chartRef" class="chart mt16"></div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { api } from '../api'

const paramFields = [
  { key: 'AT', label: '环境温度 AT', unit: '°C', min: -10, max: 40, step: 0.1, precision: 2 },
  { key: 'AP', label: '环境压力 AP', unit: 'mbar', min: 950, max: 1050, step: 0.1, precision: 2 },
  { key: 'AH', label: '环境湿度 AH', unit: '%', min: 0, max: 100, step: 0.1, precision: 2 },
  { key: 'AFDP', label: '空气过滤器差压', unit: 'mbar', min: 0, max: 12, step: 0.1, precision: 2 },
  { key: 'GTEP', label: '涡轮排气压力', unit: 'mbar', min: 10, max: 50, step: 0.1, precision: 2 },
  { key: 'TIT', label: '涡轮进口温度', unit: '°C', min: 950, max: 1150, step: 0.1, precision: 2 },
  { key: 'TAT', label: '涡轮排气温度', unit: '°C', min: 480, max: 570, step: 0.1, precision: 2 },
  { key: 'CDP', label: '压气机出口压力', unit: 'mbar', min: 5, max: 20, step: 0.1, precision: 2 }
]

const TYPICAL = {
  AT: 17.71, AP: 1013.07, AH: 77.87, AFDP: 3.93,
  GTEP: 25.56, TIT: 1081.43, TAT: 546.16, CDP: 12.06
}

const params = reactive({ ...TYPICAL })
const result = ref(null)
const loading = ref(false)
const chartRef = ref(null)
let chart = null

const metricCards = [
  { key: 'tey', label: '涡轮能量产出 TEY', unit: 'MWh', color: '#4d9fff' },
  { key: 'nox', label: 'NOX 排放浓度', unit: 'mg/m³', color: '#f56c6c' },
  { key: 'co', label: 'CO 排放浓度', unit: 'mg/m³', color: '#67c23a' }
]

function gradeType(g) {
  return { '优': 'success', '良': 'primary', '中': 'warning', '差': 'danger' }[g] || 'info'
}

function fillTypical() {
  Object.assign(params, TYPICAL)
}

async function doPredict() {
  loading.value = true
  try {
    result.value = await api.predict({ ...params })
    renderChart()
    ElMessage.success('预测完成')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!result.value || !chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const r = result.value
  chart.setOption({
    title: { text: '排放预测与限值对比', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {},
    legend: { bottom: 0, data: ['预测值', '限值'] },
    radar: {
      indicator: [
        { name: 'NOX', max: Math.max(r.nox, r.grade.nox_limit) * 1.15 },
        { name: 'CO', max: Math.max(r.co, r.grade.co_limit) * 1.15 }
      ],
      radius: '62%'
    },
    series: [{
      type: 'radar',
      data: [
        { value: [r.nox, r.co], name: '预测值', areaStyle: { opacity: 0.25 } },
        { value: [r.grade.nox_limit, r.grade.co_limit], name: '限值', lineStyle: { type: 'dashed' } }
      ]
    }]
  })
}

onMounted(async () => {
  await nextTick()
  if (result.value) renderChart()
  window.addEventListener('resize', () => chart?.resize())
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', () => chart?.resize())
  chart?.dispose()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.field-hint { font-size: 11px; color: #a0a8b4; line-height: 1; margin-top: 2px; }
.mt16 { margin-top: 16px; }
.metric {
  background: #f8fafc; border-radius: 8px; padding: 16px; text-align: center;
}
.metric-label { font-size: 13px; color: #8492a6; }
.metric-value { font-size: 26px; font-weight: 700; margin: 6px 0; }
.metric-unit { font-size: 12px; color: #a0a8b4; }
.grade-box { text-align: center; padding: 8px 0; }
.grade-label { font-size: 13px; color: #8492a6; margin-bottom: 8px; }
.grade-tag { font-size: 18px; padding: 4px 18px; }
.grade-sub { font-size: 12px; color: #a0a8b4; margin-top: 10px; }
.chart { height: 300px; }
</style>
