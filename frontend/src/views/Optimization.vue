<template>
  <div class="optimization">
    <el-row :gutter="16">
      <!-- 优化配置 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <b>优化配置</b>
              <el-button size="small" type="primary" :loading="loading" @click="doOptimize">开始优化</el-button>
            </div>
          </template>

          <el-alert type="info" :closable="false" show-icon class="mb12"
            title="以排放达标为约束，以最大化机组能量产出 TEY 为目标，使用粒子群优化算法（PSO）在参数合理区间内自动寻优。" />

          <el-form label-width="130px" size="default">
            <el-form-item label="PSO 粒子数">
              <el-slider v-model="nParticles" :min="10" :max="60" :step="5" show-input />
            </el-form-item>
            <el-form-item label="迭代次数">
              <el-slider v-model="nIterations" :min="20" :max="120" :step="10" show-input />
            </el-form-item>
          </el-form>

          <el-divider content-position="left">基准工况参数（可选，用于对比）</el-divider>
          <el-form label-width="130px" size="small">
            <el-form-item v-for="f in paramFields" :key="f.key" :label="f.label">
              <el-input-number v-model="baseline[f.key]" :min="f.min" :max="f.max"
                :step="f.step" :precision="f.precision" controls-position="right" style="width: 100%" size="small" />
            </el-form-item>
          </el-form>
          <el-button size="small" class="mt8" @click="fillTypical">填入典型工况</el-button>
        </el-card>
      </el-col>

      <!-- 优化结果 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header><b>优化结果</b></template>
          <el-empty v-if="!result" description="配置优化参数后点击「开始优化」" />
          <template v-else>
            <!-- 关键指标 -->
            <el-row :gutter="12">
              <el-col :span="8">
                <div class="metric" style="border-top: 3px solid #4d9fff">
                  <div class="metric-label">最优能量产出 TEY</div>
                  <div class="metric-value" style="color:#4d9fff">{{ result.prediction.tey.toFixed(2) }} <small>MWh</small></div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="metric" style="border-top: 3px solid #67c23a">
                  <div class="metric-label">相较基准提升</div>
                  <div class="metric-value" style="color:#67c23a">
                    +{{ (result.improvement?.tey_pct || 0).toFixed(1) }}%</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="metric" style="border-top: 3px solid #f56c6c">
                  <div class="metric-label">排放达标</div>
                  <div class="metric-value" style="color:#f56c6c">
                    <el-tag :type="result.standards_met ? 'success' : 'danger'" effect="dark">
                      {{ result.standards_met ? '达标' : '超标' }}</el-tag>
                  </div>
                </div>
              </el-col>
            </el-row>

            <!-- 对比雷达图 -->
            <div ref="chartRef" class="chart mt16"></div>

            <!-- 最优参数 -->
            <el-divider content-position="left">最优运行参数方案</el-divider>
            <el-table :data="optTable" size="small" border>
              <el-table-column prop="name" label="参数" width="200" />
              <el-table-column prop="base" label="基准值">
                <template #default="{ row }">{{ row.base != null ? row.base.toFixed(2) : '-' }}</template>
              </el-table-column>
              <el-table-column prop="optimal" label="最优值">
                <template #default="{ row }"><b style="color:#4d9fff">{{ row.optimal.toFixed(2) }}</b></template>
              </el-table-column>
              <el-table-column prop="delta" label="变化量">
                <template #default="{ row }">
                  <span :style="{ color: row.delta > 0 ? '#f56c6c' : '#67c23a' }">
                    {{ row.delta >= 0 ? '+' : '' }}{{ row.delta.toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="range" label="合理区间" width="150" />
            </el-table>
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
const RANGES = {
  AT: '[-8, 40]', AP: '[980, 1040]', AH: '[20, 102]', AFDP: '[1.5, 9]',
  GTEP: '[15, 45]', TIT: '[990, 1110]', TAT: '[500, 560]', CDP: '[9, 17]'
}
const TYPICAL = {
  AT: 17.71, AP: 1013.07, AH: 77.87, AFDP: 3.93,
  GTEP: 25.56, TIT: 1081.43, TAT: 546.16, CDP: 12.06
}

const baseline = reactive({ ...TYPICAL })
const nParticles = ref(30)
const nIterations = ref(60)
const result = ref(null)
const loading = ref(false)
const chartRef = ref(null)
let chart = null

const optTable = ref([])

function fillTypical() { Object.assign(baseline, TYPICAL) }

async function doOptimize() {
  loading.value = true
  try {
    result.value = await api.optimize({
      ...baseline,
      n_particles: nParticles.value,
      n_iterations: nIterations.value
    })
    buildTable()
    renderChart()
    ElMessage.success('优化完成')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function buildTable() {
  const opt = result.value.optimal_params
  const base = result.value.baseline?.params || {}
  optTable.value = paramFields.map(f => {
    const baseV = base[f.key]
    return {
      name: f.label,
      base: baseV != null ? baseV : null,
      optimal: opt[f.key],
      delta: baseV != null ? opt[f.key] - baseV : 0,
      range: RANGES[f.key]
    }
  })
}

function renderChart() {
  if (!result.value || !chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const opt = result.value.optimal_params
  const base = result.value.baseline?.params || {}
  const keys = paramFields.map(f => f.key)
  // 归一化用于雷达图（相对各自合理区间）
  const norm = (k, v) => {
    const [lo, hi] = RANGES[k].replace(/[\[\]]/g, '').split(', ').map(Number)
    return ((v - lo) / (hi - lo) * 100).toFixed(1)
  }
  const names = paramFields.map(f => f.label.split(' ')[0])
  chart.setOption({
    title: { text: '基准 vs 最优 参数对比（归一化）', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {},
    legend: { bottom: 0 },
    radar: { indicator: names.map(n => ({ name: n, max: 100 })), radius: '62%' },
    series: [{
      type: 'radar',
      data: [
        { value: keys.map(k => norm(k, base[k] ?? opt[k])), name: '基准工况', lineStyle: { type: 'dashed' } },
        { value: keys.map(k => norm(k, opt[k])), name: '最优方案', areaStyle: { opacity: 0.2 } }
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
.mb12 { margin-bottom: 12px; }
.mt8 { margin-top: 8px; }
.mt16 { margin-top: 16px; }
.metric { background: #f8fafc; border-radius: 8px; padding: 16px; text-align: center; }
.metric-label { font-size: 13px; color: #8492a6; }
.metric-value { font-size: 24px; font-weight: 700; margin-top: 6px; }
.metric-value small { font-size: 12px; color: #a0a8b4; font-weight: 400; }
.chart { height: 320px; }
</style>
