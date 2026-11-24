import axios from 'axios'

// 密钥只在后端保存；浏览器只携带当前用户的登录凭证。
const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api', timeout: 240000 })
api.interceptors.request.use(config => {
  const token = sessionStorage.getItem('huanuo_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
api.interceptors.response.use(response => response.data, error => {
  if (error.response?.status === 401 && !error.config?.url?.startsWith('/auth/')) {
    sessionStorage.removeItem('huanuo_token')
    window.location.assign('/login')
  }
  const detail = error.response?.data?.detail
  const message = Array.isArray(detail) ? '请检查填写内容的格式和长度' : detail
  return Promise.reject(new Error(message || (error.code === 'ECONNABORTED' ? '等待超时，请稍后检查记录或重试' : '连接失败，请确认后端服务已启动')))
})
export default api
