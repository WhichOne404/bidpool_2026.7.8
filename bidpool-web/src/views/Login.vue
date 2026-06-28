<template>
  <div class="login-page">
    <div class="login-container">
      <!-- 左侧品牌区域 -->
      <div class="brand-section">
        <div class="brand-content">
          <div class="brand-logo">
            <svg viewBox="0 0 48 48" fill="none">
              <rect width="48" height="48" rx="12" fill="#3979F6"/>
              <path d="M12 18L20 26L36 10" stroke="white" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M12 30H36" stroke="white" stroke-width="3" stroke-linecap="round"/>
            </svg>
          </div>
          <h1>BidPool</h1>
          <p>标讯智能管理平台</p>
          <div class="features">
            <div class="feature-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>智能标讯收集</span>
            </div>
            <div class="feature-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>定时任务调度</span>
            </div>
            <div class="feature-item">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>AI智能对话</span>
            </div>
          </div>
        </div>
        <div class="brand-footer">
          <span>© 2024 BidPool. All rights reserved.</span>
        </div>
      </div>

      <!-- 右侧登录区域 -->
      <div class="login-section">
        <div class="login-form-wrapper">
          <div class="login-header">
            <h2>欢迎回来</h2>
            <p>请登录您的账户以继续</p>
          </div>

          <form @submit.prevent="handleLogin" class="login-form">
            <div class="form-group">
              <label>用户名</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
                <input type="text" v-model="username" placeholder="请输入用户名" required />
              </div>
            </div>
            <div class="form-group">
              <label>密码</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <input type="password" v-model="password" placeholder="请输入密码" required />
              </div>
            </div>
            <div class="error-message" v-if="error">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {{ error }}
            </div>
            <button type="submit" class="login-btn" :disabled="loading">
              <span v-if="!loading">登录</span>
              <span v-else class="loading-spinner"></span>
            </button>
          </form>

          <div class="login-footer">
            <p>首次使用请联系管理员获取账户</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const handleLogin = async () => {
  loading.value = true
  error.value = ''

  try {
    const response = await axios.get('/api/v1/status', {
      auth: {
        username: username.value,
        password: password.value
      }
    })

    if (response.data.code === 0) {
      sessionStorage.setItem('auth', JSON.stringify({
        username: username.value,
        password: password.value,
        loginTime: new Date().toISOString()
      }))

      axios.defaults.auth = {
        username: username.value,
        password: password.value
      }

      ElMessage.success('登录成功')
      router.push('/')
    } else {
      error.value = '登录失败，请检查用户名密码'
    }
  } catch (e) {
    if (e.response?.status === 401) {
      error.value = '用户名或密码错误'
    } else {
      error.value = '网络错误，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}

const checkAuth = () => {
  const auth = sessionStorage.getItem('auth')
  if (auth) {
    const authData = JSON.parse(auth)
    username.value = authData.username
    password.value = authData.password
    axios.defaults.auth = authData
  }
}

checkAuth()
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-container {
  display: flex;
  width: 100%;
  max-width: 1000px;
  min-height: 600px;
  background: white;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15);
}

// 左侧品牌区域
.brand-section {
  flex: 1;
  background: #3979F6;
  padding: 60px 50px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  color: white;
}

.brand-content {
  .brand-logo {
    width: 64px;
    height: 64px;
    margin-bottom: 32px;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0 0 12px;
    letter-spacing: -0.02em;
  }

  p {
    font-size: 1.125rem;
    opacity: 0.9;
    margin: 0 0 48px;
  }
}

.features {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 0.9375rem;
  opacity: 0.95;

  svg {
    width: 20px;
    height: 20px;
    opacity: 0.9;
  }
}

.brand-footer {
  font-size: 0.8125rem;
  opacity: 0.7;
}

// 右侧登录区域
.login-section {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 50px;
}

.login-form-wrapper {
  width: 100%;
  max-width: 340px;
}

.login-header {
  margin-bottom: 40px;

  h2 {
    font-size: 1.75rem;
    font-weight: 600;
    color: #1e293b;
    margin: 0 0 8px;
  }

  p {
    font-size: 0.9375rem;
    color: #64748b;
    margin: 0;
  }
}

.login-form {
  .form-group {
    margin-bottom: 24px;

    label {
      display: block;
      font-size: 0.8125rem;
      font-weight: 600;
      color: #374151;
      margin-bottom: 8px;
    }
  }

  .input-wrapper {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0 16px;
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
    transition: all 0.2s;

    &:focus-within {
      border-color: #3979F6;
      box-shadow: 0 0 0 3px rgba(57, 121, 246, 0.1);
    }

    svg {
      width: 20px;
      height: 20px;
      color: #94a3b8;
      flex-shrink: 0;
    }

    input {
      flex: 1;
      border: none;
      padding: 14px 0;
      font-size: 0.9375rem;
      color: #1e293b;
      background: transparent;
      outline: none;

      &::placeholder {
        color: #94a3b8;
      }
    }
  }

  .error-message {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: #fef2f2;
    border-radius: 10px;
    color: #dc2626;
    font-size: 0.875rem;
    margin-bottom: 20px;

    svg {
      width: 18px;
      height: 18px;
      flex-shrink: 0;
    }
  }

  .login-btn {
    width: 100%;
    padding: 16px;
    background: #3979F6;
    border: none;
    border-radius: 12px;
    color: white;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;

    &:hover:not(:disabled) {
      background: #2563eb;
      transform: translateY(-1px);
    }

    &:active:not(:disabled) {
      transform: translateY(0);
    }

    &:disabled {
      opacity: 0.7;
      cursor: not-allowed;
    }

    .loading-spinner {
      display: inline-block;
      width: 20px;
      height: 20px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-top-color: white;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
  }
}

.login-footer {
  margin-top: 32px;
  text-align: center;

  p {
    font-size: 0.8125rem;
    color: #94a3b8;
    margin: 0;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

// 响应式
@media (max-width: 768px) {
  .login-container {
    flex-direction: column;
    max-width: 400px;
    min-height: auto;
  }

  .brand-section {
    padding: 40px 30px;
  }

  .brand-content h1 {
    font-size: 1.75rem;
  }

  .features {
    display: none;
  }

  .login-section {
    padding: 40px 30px;
  }
}
</style>