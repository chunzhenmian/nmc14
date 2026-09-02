<!--
  =====================================================================
  页面：异常监测（AnomalyMonitor.vue）
  =====================================================================
  左侧填 9 项工况特征（比预测多一个 TEY），点“开始检测”调 POST /api/anomaly/check；
  右侧显示正常/异常结论、预警等级、异常分值、彩色分段仪表盘，并列出历史预警日志。
  可一键填入“典型工况”或“异常工况”来体验两种结果。
-->
<template>
  <div class="anomaly">
    <el-row :gutter="16">
      <!-- ============ 左侧：工况输入（9 项） ============ -->
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
          <!-- 遍历 fields 配置自动生成 9 个数字输入框 -->
          <el-form label-width="130px" size="small">
            <el-form-item v-for="f in fields" :key="f.key" :label="f.label">
              <el-input-number v-model="params[f.key]" :min="f.min" :max="f.max"
                :step="f.step" :precision="f.precision" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-form>
          <!-- 两个快捷按钮：填正常样例 / 填异常样例 -->
          <el-button size="small" @click="fillTypical">填入典型工况</el-button>
          <!-- plain 朴素按钮、danger 红色风格，提示这是异常样例 -->
          <el-button size="small" type="danger" plain @click="fillExtreme">填入异常工况</el-button>
        </el-card>
      </el-col>

      <!-- ============ 右侧：检测结果 + 历史日志 ============ -->
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header><b>检测结果</b></template>
          <el-empty v-if="!result" description="输入工况特征后点击「开始检测」" />
          <template v-else>
            <!-- 结论横幅：:class 根据是否异常切换 ok/danger 两种配色 -->
            <div class="verdict" :class="{ danger: result.is_anomaly, ok: !result.is_anomaly }">
              <!-- 动态图标：异常显示警告、正常显示对勾 -->
              <el-icon :size="44"><component :is="result.is_anomaly ? 'WarningFilled' : 'CircleCheckFilled'" /></el-icon>
              <div class="verdict-right">
                <div class="verdict-title">{{ result.is_anomaly ? '检测到工况异常' : '工况正常' }}</div>
                <div class="verdict-sub">{{ result.description }}</div>
              </div>
            </div>

            <el-row :gutter="12" class="mt16">
              <!-- 预警等级 -->
              <el-col :span="12">
                <div class="info-box">
                  <div class="info-label">预警等级</div>
                  <el-tag :type="levelType(result.level)" size="large" effect="dark">{{ result.level }}</el-tag>
                </div>
              </el-col>
              <!-- 异常分值：小于 0 标红、否则标绿 -->
              <el-col :span="12">
                <div class="info-box">
                  <div class="info-label">异常分值（decision_function）</div>
                  <div class="info-value" :style="{ color: result.score < 0 ? '#f56c6c' : '#67c23a' }">
                    {{ result.score }} <small>（负值越远越异常）</small>
                  </div>
                </div>
              </el-col>
            </el-row>

            <!-- 异常分值彩色分段仪表盘（图由 ECharts 渲染） -->
            <div class="gauge-wrap mt16">
              <div ref="gaugeRef" class="gauge"></div>
              <!-- 图例：说明各颜色段对应的分值区间 -->
              <div class="gauge-legend">
                <span><i class="dot red"></i>高度异常 ≤ -0.35</span>
                <span><i class="dot orange"></i>中度 -0.35~-0.20</span>
                <span><i class="dot yellow"></i>轻度 -0.20~-0.10</span>
                <span><i class="dot green"></i>正常 &gt; -0.10</span>
              </div>
            </div>
          </template>
        </el-card>

        <!-- 历史预警日志表：进入页面和每次检测后刷新 -->
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

// 9 项输入特征配置（注意比预测页多了 TEY）
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

// 正常典型工况样例
const TYPICAL = {
  AT: 17.71, AP: 1013.07, AH: 77.87, AFDP: 3.93,
  GTEP: 25.56, TIT: 1081.43, TAT: 546.16, TEY: 133.51, CDP: 12.06
}
// 人为构造的异常工况样例（多项参数偏离正常区间，用于触发预警演示）
const EXTREME = {
  AT: 5.0, AP: 985.0, AH: 40.0, AFDP: 12.0,
  GTEP: 45.0, TIT: 950.0, TAT: 510.0, TEY: 60.0, CDP: 8.0
}

const params = reactive({ ...TYPICAL })  // 输入的 9 项特征
const result = ref(null)                 // 本次检测结果
const logs = ref([])                     // 历史预警日志
const loading = ref(false)
const gaugeRef = ref(null)               // 仪表盘 div
let gauge = null                         // 仪表盘 ECharts 实例

// 预警等级 → 标签颜色
function levelType(level) {
  return { '红色预警': 'danger', '橙色预警': 'warning', '黄色预警': 'warning', '正常': 'success' }[level] || 'info'
}

function fillTypical() { Object.assign(params, TYPICAL) }    // 填正常样例
function fillExtreme() { Object.assign(params, EXTREME) }    // 填异常样例

// 点击“开始检测”
async function doCheck() {
  loading.value = true
  try {
    result.value = await api.anomalyCheck({ ...params })
    await nextTick()   // 结果区是 v-if 控制的，需等它渲染出仪表盘容器后再画图
    renderGauge()
    ElMessage.success('检测完成')
    await loadLogs()   // 检测后刷新历史日志（本次记录已被后端写入）
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

// 拉取最近 20 条异常日志
async function loadLogs() {
  try {
    logs.value = await api.anomalies(20)
  } catch (e) { console.error(e) }
}

// 画异常分值仪表盘
function renderGauge() {
  if (!result.value || !gaugeRef.value) return
  // 容器还没完成布局（宽度为 0）时，等下一帧再试，避免 ECharts 因拿不到宽度而初始化失败
  if (gaugeRef.value.offsetWidth === 0) {
    requestAnimationFrame(() => renderGauge())
    return
  }
  if (!gauge) gauge = echarts.init(gaugeRef.value)
  else gauge.resize()
  const score = result.value.score
  const isAnomaly = result.value.is_anomaly
  // 仪表盘量程取 [-0.6, 0.3]，总跨度 0.9。ECharts 色环的分界点要用“占总跨度的比例”表示，
  // 所以把各预警阈值换算成比例：
  //   -0.35 → (-0.35-(-0.6))/0.9 = 0.2778（红/橙分界）
  //   -0.20 → 0.4444（橙/黄分界）
  //   -0.10 → 0.5556（黄/绿分界），其余到 1 为绿色正常区
  gauge.setOption({
    series: [{
      type: 'gauge',
      min: -0.6, max: 0.3,
      startAngle: 210, endAngle: -30,   // 起止角度，做成接近 240° 的弧形表盘
      radius: '70%',
      center: ['50%', '50%'],
      splitNumber: 9,
      axisLine: {
        roundCap: true,                 // 色带两端圆角
        lineStyle: {
          width: 14,
          // 分段色环：[累计比例, 颜色]，与红橙黄绿预警等级一一对应
          color: [
            [0.2778, '#f56c6c'],
            [0.4444, '#e6a23c'],
            [0.5556, '#f5d96b'],
            [1, '#67c23a']
          ]
        }
      },
      pointer: { length: '60%', width: 4, itemStyle: { color: '#303133' } },  // 指针样式
      anchor: {
        show: true, size: 10,
        itemStyle: { color: '#303133', borderColor: '#fff', borderWidth: 2 }  // 指针中心圆点
      },
      axisTick: { length: 4, splitNumber: 1, lineStyle: { color: '#909399', width: 1 } },   // 小刻度
      splitLine: { length: 10, lineStyle: { color: '#606266', width: 2 } },                // 主刻度
      axisLabel: {
        distance: 14, fontSize: 10, color: '#606266',
        // 只在每隔 0.2 的位置显示刻度数字，其余返回空串，避免顶部弧段数字拥挤重叠
        formatter: (v) => {
          const t = Math.round(v * 100)
          return (t % 20 === 0 || t === 30) ? v.toFixed(1) : ''
        }
      },
      title: { offsetCenter: [0, '78%'], fontSize: 12, color: '#909399' },    // 表盘下方标题
      detail: {
        valueAnimation: true,                  // 数值变化时有滚动动画
        offsetCenter: [0, '52%'],
        fontSize: 24,
        fontWeight: 'bold',
        color: isAnomaly ? '#f56c6c' : '#67c23a',  // 数值颜色随结论变化
        formatter: (v) => v.toFixed(4)             // 中央数值保留 4 位小数
      },
      data: [{ value: score, name: '异常分值（越负越异常）' }]
    }]
  })
}

// 挂载后：等 DOM 就绪 → 先加载历史日志 → 若已有结果则补画仪表盘，并监听窗口缩放
onMounted(async () => {
  await nextTick()
  await loadLogs()
  if (result.value) renderGauge()
  window.addEventListener('resize', () => gauge?.resize())
})
// 离开前移除监听并销毁仪表盘，释放资源
onBeforeUnmount(() => {
  window.removeEventListener('resize', () => gauge?.resize())
  gauge?.dispose()
})
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.mb12 { margin-bottom: 12px; }
.mt16 { margin-top: 16px; }
/* 结论横幅：flex 横向排列图标和文字 */
.verdict {
  display: flex; align-items: center; gap: 16px;
  padding: 18px; border-radius: 10px;
}
.verdict.ok { background: #f0f9eb; color: #67c23a; }       /* 正常：浅绿 */
.verdict.danger { background: #fef0f0; color: #f56c6c; }   /* 异常：浅红 */
.verdict-title { font-size: 20px; font-weight: 700; }
.verdict-sub { font-size: 13px; color: #606266; margin-top: 4px; }
.info-box { background: #f8fafc; border-radius: 8px; padding: 14px 16px; }
.info-label { font-size: 12px; color: #8492a6; margin-bottom: 8px; }
.info-value { font-size: 20px; font-weight: 700; }
.info-value small { font-size: 12px; font-weight: 400; color: #a0a8b4; }
.gauge-wrap { display: flex; flex-direction: column; align-items: center; }
.gauge { height: 240px; width: 100%; }   /* 仪表盘高度固定、宽度撑满 */
/* 图例区：自动换行、居中、各项间距 16px */
.gauge-legend {
  display: flex; flex-wrap: wrap; gap: 16px; justify-content: center;
  margin-top: 4px; font-size: 12px; color: #606266;
}
.gauge-legend span { display: inline-flex; align-items: center; gap: 5px; }
.gauge-legend .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }  /* 圆形色点 */
.dot.red { background: #f56c6c; }
.dot.orange { background: #e6a23c; }
.dot.yellow { background: #f5d96b; }
.dot.green { background: #67c23a; }
</style>
