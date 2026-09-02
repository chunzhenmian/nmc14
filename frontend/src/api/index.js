// =====================================================================
// 后端接口统一封装（api/index.js）
// =====================================================================
// 页面不直接写网址请求后端，而是调用这里的方法，好处是后端地址集中管理、
// 出错提示统一处理。底层用 axios（一个发 HTTP 请求的工具库）。
// =====================================================================
import axios from 'axios'

// 创建一个统一的 axios 实例：
//  baseURL='/api'：所有请求自动在前面拼 /api；
//  开发时 vite 会把 /api 开头的请求转发到后端 5000 端口（见 vite.config.js 的 proxy），
//  这样前端 5173 端口访问后端也不会有跨域问题。
//  timeout=60000：请求超过 60 秒没响应就判定超时（PSO 优化可能稍慢，给足时间）。
const http = axios.create({
  baseURL: '/api',
  timeout: 60000
})

// 响应拦截器：每个请求返回后先经过这里统一处理
http.interceptors.response.use(
  (res) => res.data,                       // 成功：直接把响应体 data 返回，页面拿到的就是后端 JSON
  (err) => {                               // 失败：提取后端返回的错误信息，统一抛成 Error
    // ?. 是“可选链”：err.response 不存在时不会报错，而是返回 undefined
    const msg = err.response?.data?.error || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  }
)

// ---------- 接口方法：方法名和后端 9 个接口一一对应 ----------
export const api = {
  // 健康检查（GET）
  health: () => http.get('/health'),
  // 运行总览（GET）
  overview: () => http.get('/overview'),
  // 排放预测（POST，params 是 8 项运行参数对象）
  predict: (params) => http.post('/predict', params),
  // 参数优化（POST，可带基准参数和粒子数/迭代次数）
  optimize: (params) => http.post('/optimize', params),
  // 工况异常检测（POST，params 是 9 项特征）
  anomalyCheck: (params) => http.post('/anomaly/check', params),
  // 历史记录（GET；第二个参数会被拼成 ?type=xxx&limit=50）
  records: (type, limit = 50) => http.get('/records', { params: { type, limit } }),
  // 异常日志（GET）
  anomalies: (limit = 50) => http.get('/anomalies', { params: { limit } }),
  // 设备信息（GET）
  device: () => http.get('/device'),
  // 模型评估信息（GET）
  modelInfo: () => http.get('/model/info')
}

export default api   // 默认导出，页面里 import api 即可使用
