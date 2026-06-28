import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import axios from 'axios'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// 注册Element Plus图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 配置 axios 自动添加认证
const auth = sessionStorage.getItem('auth')
if (auth) {
  const authData = JSON.parse(auth)
  axios.defaults.auth = {
    username: authData.username,
    password: authData.password
  }
}

// axios 请求拦截器 - 自动添加认证
axios.interceptors.request.use(config => {
  const authData = sessionStorage.getItem('auth')
  if (authData) {
    const auth = JSON.parse(authData)
    config.auth = {
      username: auth.username,
      password: auth.password
    }
  }
  return config
})

// axios 响应拦截器 - 处理401错误
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem('auth')
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

app.use(ElementPlus)
app.use(router)
app.mount('#app')