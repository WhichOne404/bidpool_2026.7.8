import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  auth: {
    username: 'admin',
    password: 'bidpool@2026'
  }
})

// Chat API 使用独立的实例（不带 baseURL）
const chatAxios = axios.create({
  timeout: 30000
})

// Chat API 响应拦截器
chatAxios.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    return Promise.reject(error)
  }
)

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    return Promise.reject(error)
  }
)

// 任务API
export const taskApi = {
  list: () => api.get('/tasks'),
  get: (id) => api.get(`/tasks/${id}`),
  create: (data) => api.post('/tasks', data),
  update: (id, data) => api.put(`/tasks/${id}`, data),
  delete: (id) => api.delete(`/tasks/${id}`),
  run: (id) => api.post(`/tasks/${id}/run`)
}

// 标讯API
export const bidApi = {
  list: (params) => api.get('/bids', { params }),
  get: (id) => api.get(`/bids/${id}`),
  delete: (id) => api.delete(`/bids/${id}`),
  batchDelete: (ids) => api.post('/bids/batch-delete', { ids }),
  dispatch: (data) => api.post('/bids/dispatch', data)
}

// 配置API
export const configApi = {
  get: () => api.get('/config'),
  save: (data) => api.post('/config', data),
  testDingTalk: (webhook_url) => api.post('/config/dingtalk/test', { webhook_url })
}

// 对话API - 使用独立的 axios 实例
export const chatApi = {
  send: (message, sessionId) => chatAxios.post('/chat/', { message, session_id: sessionId }),
  welcome: () => chatAxios.get('/chat/welcome/')
}

// 状态API
export const statusApi = {
  get: () => api.get('/status')
}

export default api