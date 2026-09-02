<!--
  =====================================================================
  页面：排放预测（Prediction.vue）
  =====================================================================
  左侧填 8 项运行参数（数字输入框），点“开始预测”调 POST /api/predict；
  右侧显示 TEY/NOX/CO 三个结果、综合排放等级、达标判定，并用雷达图对比预测值与限值。
-->
<template>
  <div class="prediction">
    <el-row :gutter="16">
      <!-- ============ 左侧：参数输入（占 10/24） ============ -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <b>运行参数输入</b>
              <div>
                <!-- 一键填入一组典型工况，免去手动逐个输入 -->
                <el-button size="small" @click="fillTypical">填入典型工况</el-button>
                <!-- :loading 提交时按钮转圈，防止重复点击 -->
                <el-button size="small" type="primary" :loading="loading" @click="doPredict">开始预测</el-button>
              </div>
            </div>
          </template>
          <!-- v-for 根据 paramFields 配置自动生成 8 个输入项，避免手写 8 遍 -->
          <el-form label-width="120px" size="default">
            <el-form-item v-for="f in paramFields" :key="f.key" :label="f.label">
              <!-- el-input-number 数字输入框，v-model 双向绑定到 params 对应字段；
                   :min/:max 限制范围、:step 步进、:precision 小数位数 -->
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

      <!-- ============ 右侧：预测结果（占 14/24） ============ -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header><b>预测结果</b></template>
          <!-- 还没预测时显示空状态提示 -->
          <el-empty v-if="!result" description="输入运行参数后点击「开始预测」" />
          <!-- v-else：有结果后才渲染下面内容 -->
          <template v-else>
            <!-- 三个结果指标卡，遍历 metricCards 生成 -->
            <el-row :gutter="12">
              <el-col :span="8" v-for="m in metricCards" :key="m.key">
                <div class="metric" :style="{ borderTop: '3px solid ' + m.color }">
                  <div class="metric-label">{{ m.label }}</div>
                  <!-- ?. 可选链 + toFixed(2)：结果保留两位小数显示 -->
                  <div class="metric-value" :style="{ color: m.color }">{{ result[m.key]?.toFixed(2) }}</div>
                  <div class="metric-unit">{{ m.unit }}</div>
                </div>
              </el-col>
            </el-row>

            <el-row :gutter="12" class="mt16">
              <!-- 综合排放等级 -->
              <el-col :span="12">
                <el-card shadow="never" class="grade-box">
                  <div class="grade-label">综合排放等级</div>
                  <!-- 等级文字决定标签颜色（gradeType 映射） -->
                  <el-tag :type="gradeType(result.grade.overall)" size="large" effect="dark" class="grade-tag">
                    {{ result.grade.overall }}
                  </el-tag>
                  <div class="grade-sub">
                    CO：{{ result.grade.co_grade }} / NOX：{{ result.grade.nox_grade }}
                  </div>
                </el-card>
              </el-col>
              <!-- 达标判定：三元表达式根据 standards_met 显示绿色达标/红色超标 -->
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

            <!-- 预测值 vs 限值 雷达对比图 -->
            <div ref="chartRef" class="chart mt16"></div>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
// reactive 用来定义“对象型”响应式数据（ref 更适合基本类型，这里 params 是对象）
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'   // 右上角轻提示（成功/失败消息）
import { api } from '../api'

// 8 个输入项的配置：字段名、中文名、单位、取值范围、步长、精度。页面据此自动生成表单
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

// 一组典型工况数值，点“填入典型工况”时使用
const TYPICAL = {
  AT: 17.71, AP: 1013.07, AH: 77.87, AFDP: 3.93,
  GTEP: 25.56, TIT: 1081.43, TAT: 546.16, CDP: 12.06
}

const params = reactive({ ...TYPICAL })  // 表单数据，初始就填入典型值（... 是展开复制）
const result = ref(null)                 // 预测结果，初始为空
const loading = ref(false)               // 是否正在请求（控制按钮 loading）
const chartRef = ref(null)               // 雷达图 div 引用
let chart = null                         // 雷达图实例

// 三个结果指标卡的展示配置（key 对应后端返回的字段名）
const metricCards = [
  { key: 'tey', label: '涡轮能量产出 TEY', unit: 'MWh', color: '#4d9fff' },
  { key: 'nox', label: 'NOX 排放浓度', unit: 'mg/m³', color: '#f56c6c' },
  { key: 'co', label: 'CO 排放浓度', unit: 'mg/m³', color: '#67c23a' }
]

// 排放等级 → Element 标签颜色
function gradeType(g) {
  return { '优': 'success', '良': 'primary', '中': 'warning', '差': 'danger' }[g] || 'info'
}

// 一键填入典型工况：Object.assign 把 TYPICAL 的值覆盖到 params
function fillTypical() {
  Object.assign(params, TYPICAL)
}

// 点击“开始预测”：提交参数 → 拿结果 → 画图 → 提示
async function doPredict() {
  loading.value = true                 // 进入加载状态
  try {
    result.value = await api.predict({ ...params })  // 展开 params 作为请求体提交
    renderChart()                      // 拿到结果后画雷达图
    ElMessage.success('预测完成')
  } catch (e) {
    ElMessage.error(e.message)         // 失败时弹出后端返回的错误信息
  } finally {
    loading.value = false              // 无论成功失败都关闭 loading
  }
}

// 画“预测值 vs 限值”雷达图（NOX、CO 两个维度）
function renderChart() {
  if (!result.value || !chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const r = result.value
  chart.setOption({
    title: { text: '排放预测与限值对比', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {},
    legend: { bottom: 0, data: ['预测值', '限值'] },
    radar: {
      // 每个轴的最大值取“预测值和限值中较大者 ×1.15”，留出余量保证图形好看
      indicator: [
        { name: 'NOX', max: Math.max(r.nox, r.grade.nox_limit) * 1.15 },
        { name: 'CO', max: Math.max(r.co, r.grade.co_limit) * 1.15 }
      ],
      radius: '62%'
    },
    series: [{
      type: 'radar',
      data: [
        { value: [r.nox, r.co], name: '预测值', areaStyle: { opacity: 0.25 } },  // 实心填充
        { value: [r.grade.nox_limit, r.grade.co_limit], name: '限值', lineStyle: { type: 'dashed' } } // 虚线
      ]
    }]
  })
}

// 挂载后：若已有结果则补画图表，并监听窗口缩放
onMounted(async () => {
  await nextTick()
  if (result.value) renderChart()
  window.addEventListener('resize', () => chart?.resize())
})
// 离开前清理图表
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
