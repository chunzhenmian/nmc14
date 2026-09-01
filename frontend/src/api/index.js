import axios from 'axios'

// 统一 axios 实例：开发环境经 vite 代理 /api → 后端 5000 端口
const http = axios.create({
  baseURL: '/api',
  timeout: 60000
})

http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.error || err.message || '请求失败'
    return Promise.reject(new Error(msg))
  }
)

// ---------- 接口方法 ----------
export const api = {
  // 健康检查
  health: () => http.get('/health'),
  // 运行总览
  overview: () => http.get('/overview'),
  // 排放预测
  predict: (params) => http.post('/predict', params),
  // 参数优化
  optimize: (params) => http.post('/optimize', params),
  // 工况异常检测
  anomalyCheck: (params) => http.post('/anomaly/check', params),
  // 历史记录
  records: (type, limit = 50) => http.get('/records', { params: { type, limit } }),
  // 异常日志
  anomalies: (limit = 50) => http.get('/anomalies', { params: { limit } }),
  // 设备信息
  device: () => http.get('/device'),
  // 模型信息
  modelInfo: () => http.get('/model/info')
}

export default api
