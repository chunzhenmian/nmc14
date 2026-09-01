<template>
  <div class="anomaly">
    <el-row :gutter="16">
      <!-- 工况输入 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <b>工况监测输入（9 项特征）</b>
              <el-button size="small" type="primary" :loading="loading" @click="doCheck">开始检测</el-button>
            </div>
          </template>
          <el-alert type="warning" :closable="false" show-icon class="mb12"
            title="基于正常工况数据构建的孤立森林模型，识别偏离正常分布的工况异常与排放异常。" />
          <el-form label-width="130px" size="small">
            <el-form-item v-for="f in fields" :key="f.key" :label="f.label">
              <el-input-number v-model="params[f.key]" :min="f.min" :max="f.max"
                :step="f.step" :precision="f.precision" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-form>
          <el-button size="small" @click="fillTypical">填入典型工况</el-button>
          <el-button size="small" type="danger" plain @click="fillExtreme">填入异常工况</el-button>
        </el-card>
      </el-col>

      <!-- 检测结果 -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header><b>检测结果</b></template>
          <el-empty v-if="!result" description="输入工况特征后点击「开始检测」" />
          <template v-else>
            <div class="verdict" :class="{ danger: result.is_anomaly, ok: !result.is_anomaly }">
              <el-icon :size="44"><component :is="result.is_anomaly ? 'WarningFilled' : 'CircleCheckFilled'" /></el-icon>
              <div class="verdict-right">
                <div class="verdict-title">{{ result.is_anomaly ? '检测到工况异常' : '工况正常' }}</div>
                <div class="verdict-sub">{{ result.description }}</div>
              </div>
            </div>

            <el-row :gutter="12" class="mt16">
              <el-col :span="12">
                <div class="info-box">
                  <div class="info-label">预警等级</div>
                  <el-tag :type="levelType(result.level)" size="large" effect="dark">{{ result.level }}</el-tag>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="info-box">
                  <div class="info-label">异常分值（decision_function）</div>
                  <div class="info-value" :style="{ color: result.score < 0 ? '#f56c6c' : '#67c23a' }">
                    {{ result.score }} <small>（负值越远越异常）</small>
                  </div>
                </div>
              </el-col>
            </el-row>

            <!-- 异常分值仪表 -->
            <div ref="gaugeRef" class="gauge mt16"></div>
          </template>
        </el-card>

        <!-- 历史预警日志 -->
        <el-card shadow="hover" class="mt16">
          <template #header><b>历史预警日志</b></template>
          <el-table :data="logs" size="small" empty-text="暂无预警记录">
            <el-table-column prop="id" label="ID" width="70" />
            <el-table-column prop="level" label="等级" width="100">
              <template #default="{ row }">
                <el-tag :type="levelType(row.level)" effect="dark">{{ row.level }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="异常分值" width="110">
              <template #default="{ row }">{{ row.score }}</template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="240" />
            <el-table-column prop="created_at" label="时间" width="175" />
          </el-table>
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

const fields = [
  { key: 'AT', label: '环境温度 AT', min: -10, max: 40, step: 0.1, precision: 2 },
  { key: 'AP', label: '环境压力 AP', min: 950, max: 1050, step: 0.1, precision: 2 },
  { key: 'AH', label: '环境湿度 AH', min: 0, max: 100, step: 0.1, precision: 2 },
  { key: 'AFDP', label: '空气过滤器差压', min: 0, max: 15, step: 0.1, precision: 2 },
  { key: 'GTEP', label: '涡轮排气压力', min: 10, max: 55, step: 0.1, precision: 2 },
  { key: 'TIT', label: '涡轮进口温度', min: 800, max: 1150, step: 0.1, precision: 2 },
  { key: 'TAT', label: '涡轮排气温度', min: 450, max: 570, step: 0.1, precision: 2 },
  { key: 'TEY', label: '涡轮能量产出 TEY', min: 20, max: 220, step: 0.1, precision: 2 },
  { key: 'CDP', label: '压气机出口压力', min: 3, max: 22, step: 0.1, precision: 2 }
]

const TYPICAL = {
  AT: 17.71, AP: 1013.07, AH: 77.87, AFDP: 3.93,
  GTEP: 25.56, TIT: 1081.43, TAT: 546.16, TEY: 133.51, CDP: 12.06
}
const EXTREME = {
  AT: 5.0, AP: 985.0, AH: 40.0, AFDP: 12.0,
  GTEP: 45.0, TIT: 950.0, TAT: 510.0, TEY: 60.0, CDP: 8.0
}

const params = reactive({ ...TYPICAL })
const result = ref(null)
const logs = ref([])
const loading = ref(false)
const gaugeRef = ref(null)
let gauge = null

function levelType(level) {
  return { '红色预警': 'danger', '橙色预警': 'warning', '黄色预警': 'warning', '正常': 'success' }[level] || 'info'
}

function fillTypical() { Object.assign(params, TYPICAL) }
function fillExtreme() { Object.assign(params, EXTREME) }

async function doCheck() {
  loading.value = true
  try {
    result.value = await api.anomalyCheck({ ...params })
    renderGauge()
    ElMessage.success('检测完成')
    await loadLogs()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function loadLogs() {
  try {
    logs.value = await api.anomalies(20)
  } catch (e) { console.error(e) }
}

function renderGauge() {
  if (!result.value || !gaugeRef.value) return
  if (!gauge) gauge = echarts.init(gaugeRef.value)
  const score = result.value.score
  gauge.setOption({
    series: [{
      type: 'gauge',
      min: -0.6, max: 0.3,
      splitNumber: 6,
      axisLine: { lineStyle: { color: [[0.5, '#f56c6c'], [0.8, '#e6a23c'], [1, '#67c23a']] } },
      pointer: { length: '60%', width: 5 },
      axisTick: { splitNumber: 5 },
      detail: { formatter: '{value}', fontSize: 18 },
      title: { offsetCenter: [0, '78%'], fontSize: 13 },
      data: [{ value: score, name: '异常分值' }]
    }]
  })
}

onMounted(async () => {
  await nextTick()
  await loadLogs()
  if (result.value) renderGauge()
  window.addEventListener('resize', () => gauge?.resize())
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', () => gauge?.resize())
  gauge?.dispose()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.mb12 { margin-bottom: 12px; }
.mt16 { margin-top: 16px; }
.verdict {
  display: flex; align-items: center; gap: 16px;
  padding: 18px; border-radius: 10px;
}
.verdict.ok { background: #f0f9eb; color: #67c23a; }
.verdict.danger { background: #fef0f0; color: #f56c6c; }
.verdict-title { font-size: 20px; font-weight: 700; }
.verdict-sub { font-size: 13px; color: #606266; margin-top: 4px; }
.info-box { background: #f8fafc; border-radius: 8px; padding: 14px 16px; }
.info-label { font-size: 12px; color: #8492a6; margin-bottom: 8px; }
.info-value { font-size: 20px; font-weight: 700; }
.info-value small { font-size: 12px; font-weight: 400; color: #a0a8b4; }
.gauge { height: 220px; }
</style>
