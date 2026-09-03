<!--
  =====================================================================
  页面：参数优化（Optimization.vue）
  =====================================================================
  左侧设置 PSO 粒子数、迭代次数和可选的基准工况；点“开始优化”调 POST /api/optimize。
  右侧显示最优 TEY、相较基准提升百分比、是否达标，并用归一化雷达图对比基准与最优方案，
  表格列出每个参数的基准值、最优值、变化量和合理区间。
-->
<template>
  <div class="optimization">
    <el-row :gutter="16">
      <!-- ============ 左侧：优化配置 ============ -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <b>优化配置</b>
              <el-button size="small" type="primary" :loading="loading" @click="doOptimize">开始优化</el-button>
            </div>
          </template>

          <!-- 说明条：讲清优化目标与约束 -->
          <el-alert type="info" :closable="false" show-icon class="mb12"
            title="以排放达标为约束，以最大化机组能量产出 TEY 为目标，使用粒子群优化算法（PSO）在参数合理区间内自动寻优。" />

          <el-form label-width="130px" size="default">
            <!-- 滑块 + 数字输入（show-input）调节 PSO 超参数 -->
            <el-form-item label="PSO 粒子数">
              <el-slider v-model="nParticles" :min="10" :max="60" :step="5" show-input />
            </el-form-item>
            <el-form-item label="迭代次数">
              <el-slider v-model="nIterations" :min="20" :max="120" :step="10" show-input />
            </el-form-item>
          </el-form>

          <!-- 分割线：下面是可选的基准工况，用于做优化前后对比 -->
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

      <!-- ============ 右侧：优化结果 ============ -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header><b>优化结果</b></template>
          <el-empty v-if="!result" description="配置优化参数后点击「开始优化」" />
          <template v-else>
            <!-- 三个关键指标卡 -->
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
                    <!-- improvement 可能不存在（未给基准），用 || 0 兜底 -->
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

            <!-- 基准 vs 最优 雷达图 -->
            <div ref="chartRef" class="chart mt16"></div>

            <!-- 最优参数对比表 -->
            <el-divider content-position="left">最优运行参数方案</el-divider>
            <!-- :data 绑定 buildTable 生成的表格行 -->
            <el-table :data="optTable" size="small" border>
              <el-table-column prop="name" label="参数" width="200" />
              <el-table-column prop="base" label="基准值">
                <!-- 作用域插槽自定义显示：无基准时显示 '-' -->
                <template #default="{ row }">{{ row.base != null ? row.base.toFixed(2) : '-' }}</template>
              </el-table-column>
              <el-table-column prop="optimal" label="最优值">
                <template #default="{ row }"><b style="color:#4d9fff">{{ row.optimal.toFixed(2) }}</b></template>
              </el-table-column>
              <el-table-column prop="delta" label="变化量">
                <template #default="{ row }">
                  <!-- 上升标红、下降标绿；非负数前补 '+' 号 -->
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

// 8 个基准参数输入项的配置（与预测页一致）
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
// 各参数的合理寻优区间（字符串形式，表格直接展示；画图时再解析成数字）
const RANGES = {
  AT: '[-8, 40]', AP: '[980, 1040]', AH: '[20, 102]', AFDP: '[1.5, 9]',
  GTEP: '[15, 45]', TIT: '[990, 1110]', TAT: '[500, 560]', CDP: '[9, 17]'
}
// 典型工况默认值
const TYPICAL = {
  AT: 17.71, AP: 1013.07, AH: 77.87, AFDP: 3.93,
  GTEP: 25.56, TIT: 1081.43, TAT: 546.16, CDP: 12.06
}

const baseline = reactive({ ...TYPICAL })  // 基准工况参数
const nParticles = ref(30)                  // PSO 粒子数，默认 30
const nIterations = ref(60)                 // 迭代次数，默认 60
const result = ref(null)                    // 优化结果
const loading = ref(false)                  // 请求加载状态
const chartRef = ref(null)                  // 雷达图 div
let chart = null

const optTable = ref([])                    // 参数对比表数据

function fillTypical() { Object.assign(baseline, TYPICAL) }  // 一键填典型工况

// 点击“开始优化”
async function doOptimize() {
  loading.value = true
  try {
    // 把基准参数和 PSO 超参数一起提交给后端
    result.value = await api.optimize({
      ...baseline,
      n_particles: nParticles.value,
      n_iterations: nIterations.value
    })
    buildTable()    // 生成参数对比表
    await nextTick()  // 等 v-if 的图表容器挂载完成，否则 echarts 找不到节点
    renderChart()   // 画雷达图
    ElMessage.success('优化完成')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

// 根据返回结果拼出表格行：参数名、基准值、最优值、变化量、合理区间
function buildTable() {
  const opt = result.value.optimal_params
  const base = result.value.baseline?.params || {}
  optTable.value = paramFields.map(f => {       // map：逐个参数生成一行
    const baseV = base[f.key]
    return {
      name: f.label,
      base: baseV != null ? baseV : null,       // 没有基准就置 null（页面显示 '-'）
      optimal: opt[f.key],
      delta: baseV != null ? opt[f.key] - baseV : 0,  // 变化量=最优-基准
      range: RANGES[f.key]
    }
  })
}

// 画“基准 vs 最优”归一化雷达图
function renderChart() {
  if (!result.value || !chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const opt = result.value.optimal_params
  const base = result.value.baseline?.params || {}
  const keys = paramFields.map(f => f.key)
  // 归一化：各参数量纲不同（温度上千、湿度几十），统一换算成“在自身区间内的百分位 0~100”，
  // 这样才能在同一张雷达图里比较。先把 '[lo, hi]' 字符串解析成两个数字
  const norm = (k, v) => {
    const [lo, hi] = RANGES[k].replace(/[\[\]]/g, '').split(', ').map(Number)
    return ((v - lo) / (hi - lo) * 100).toFixed(1)
  }
  const names = paramFields.map(f => f.label.split(' ')[0])  // 雷达轴名取参数中文名部分
  chart.setOption({
    title: { text: '基准 vs 最优 参数对比（归一化）', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {},
    legend: { bottom: 0 },
    radar: { indicator: names.map(n => ({ name: n, max: 100 })), radius: '62%' },  // 每轴上限 100
    series: [{
      type: 'radar',
      data: [
        // base[k] ?? opt[k]：基准缺该参数时用最优值兜底，避免画出 undefined
        { value: keys.map(k => norm(k, base[k] ?? opt[k])), name: '基准工况', lineStyle: { type: 'dashed' } },
        { value: keys.map(k => norm(k, opt[k])), name: '最优方案', areaStyle: { opacity: 0.2 } }
      ]
    }]
  })
}

// 挂载/卸载时的图表初始化与清理
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
