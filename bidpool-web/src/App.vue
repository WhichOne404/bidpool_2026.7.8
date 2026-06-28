<template>
  <!-- 登录页面直接显示内容 -->
  <router-view v-if="route.path === '/login'" />

  <!-- 其他页面显示完整布局 -->
  <el-container v-else class="app-container">
    <!-- Sidebar -->
    <el-aside :width="sidebarCollapsed ? '70px' : '220px'" class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="32" height="32" rx="8" fill="url(#logo-gradient)"/>
              <path d="M8 12L14 18L24 8" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M8 20H24" stroke="white" stroke-width="2" stroke-linecap="round"/>
              <defs>
                <linearGradient id="logo-gradient" x1="0" y1="0" x2="32" y2="32">
                  <stop stop-color="#3979F6"/>
                  <stop offset="1" stop-color="#6291e3"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <transition name="fade">
            <div v-if="!sidebarCollapsed" class="logo-text">
              <span class="logo-name">BidPool</span>
              <span class="logo-sub">标讯智能平台</span>
            </div>
          </transition>
        </div>
      </div>

      <nav class="sidebar-nav">
        <div class="nav-section">
          <router-link to="/" class="nav-item" :class="{ active: activeMenu === '/' }">
            <div class="nav-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7" rx="1"/>
                <rect x="14" y="3" width="7" height="7" rx="1"/>
                <rect x="3" y="14" width="7" height="7" rx="1"/>
                <rect x="14" y="14" width="7" height="7" rx="1"/>
              </svg>
            </div>
            <transition name="fade">
              <span v-if="!sidebarCollapsed">仪表盘</span>
            </transition>
          </router-link>
          <router-link to="/tasks" class="nav-item" :class="{ active: activeMenu === '/tasks' }">
            <div class="nav-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                <line x1="16" y1="2" x2="16" y2="6"/>
                <line x1="8" y1="2" x2="8" y2="6"/>
                <line x1="3" y1="10" x2="21" y2="10"/>
              </svg>
            </div>
            <transition name="fade">
              <span v-if="!sidebarCollapsed">任务管理</span>
            </transition>
          </router-link>
          <router-link to="/bids" class="nav-item" :class="{ active: activeMenu === '/bids' }">
            <div class="nav-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
            </div>
            <transition name="fade">
              <span v-if="!sidebarCollapsed">标讯列表</span>
            </transition>
          </router-link>
        </div>

        <div class="nav-section">
          <transition name="fade">
            <span v-if="!sidebarCollapsed" class="nav-section-title">智能助手</span>
          </transition>
          <router-link to="/chat" class="nav-item" :class="{ active: activeMenu === '/chat' }">
            <div class="nav-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <transition name="fade">
              <span v-if="!sidebarCollapsed">智能对话</span>
            </transition>
            <transition name="fade">
              <span v-if="!sidebarCollapsed" class="nav-badge">AI</span>
            </transition>
          </router-link>
        </div>

        <div class="nav-section">
          <transition name="fade">
            <span v-if="!sidebarCollapsed" class="nav-section-title">系统</span>
          </transition>
          <router-link to="/settings" class="nav-item" :class="{ active: activeMenu === '/settings' }">
            <div class="nav-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
              </svg>
            </div>
            <transition name="fade">
              <span v-if="!sidebarCollapsed">系统设置</span>
            </transition>
          </router-link>
          <router-link to="/api-docs" class="nav-item" :class="{ active: activeMenu === '/api-docs' }">
            <div class="nav-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
            </div>
            <transition name="fade">
              <span v-if="!sidebarCollapsed">API文档</span>
            </transition>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <div class="collapse-btn" @click="sidebarCollapsed = !sidebarCollapsed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
            <polyline :points="sidebarCollapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"/>
          </svg>
        </div>
        <transition name="fade">
          <div v-if="!sidebarCollapsed" class="version">v1.0.0</div>
        </transition>
      </div>
    </el-aside>

    <!-- Main Content -->
    <el-container class="main-wrapper">
      <el-header class="top-bar">
        <div class="top-bar-left">
          <h1>{{ pageTitle }}</h1>
        </div>
        <div class="top-bar-right">
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span class="status-text">系统正常运行</span>
          </div>
          <div class="current-time">
            {{ currentTime }}
          </div>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeMenu = computed(() => route.path)
const currentTime = ref('')
const sidebarCollapsed = ref(false)

const pageTitle = computed(() => {
  const titles = {
    '/': '仪表盘',
    '/tasks': '任务管理',
    '/bids': '标讯列表',
    '/chat': '智能对话',
    '/settings': '系统设置',
    '/api-docs': 'API文档'
  }
  return titles[route.path] || 'BidPool'
})

let timer = null

const updateTime = () => {
  currentTime.value = new Date().toLocaleString('zh-CN', {
    hour12: false,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style>
@import './styles/light-blue.scss';

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-weight: 400;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app-container {
  height: 100vh;
  background: #f5f7fa;
}

/* Sidebar */
.sidebar {
  background: #ffffff;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: width 0.3s ease;
  border-right: 1px solid #e8e8ef;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

.sidebar-header {
  padding: 24px 20px;
  border-bottom: 1px solid #f0f0f5;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-name {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.02em;
}

.logo-sub {
  font-size: 11px;
  color: #8a8aa3;
  margin-top: 2px;
}

/* Navigation */
.sidebar-nav {
  flex: 1;
  padding: 20px 12px;
  overflow-y: auto;
}

.nav-section {
  margin-bottom: 24px;
}

.nav-section-title {
  display: block;
  font-size: 10px;
  font-weight: 700;
  color: #8a8aa3;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0 12px;
  margin-bottom: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #4a4a6a;
  text-decoration: none;
  transition: all 0.15s;
  margin-bottom: 4px;
}

.nav-item:hover {
  background: #f5f7fa;
  color: #1a1a2e;
}

.nav-item.active {
  background: rgba(57, 121, 246, 0.1);
  color: #3979F6;
  font-weight: 600;
}

.nav-item.active .nav-icon {
  color: #3979F6;
}

.nav-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-icon svg {
  width: 20px;
  height: 20px;
}

.nav-badge {
  margin-left: auto;
  padding: 2px 8px;
  background: linear-gradient(135deg, #3979F6 0%, #6291e3 100%);
  color: white;
  font-size: 10px;
  font-weight: 600;
  border-radius: 10px;
}

/* Sidebar Footer */
.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid #f0f0f5;
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  color: #8a8aa3;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.collapse-btn:hover {
  background: #e8e8ef;
  color: #1a1a2e;
}

.version {
  font-size: 12px;
  color: #8a8aa3;
}

/* Main Content */
.main-wrapper {
  background: transparent;
}

.top-bar {
  height: 64px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8ef;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.top-bar-left h1 {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0;
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(71, 130, 43, 0.1);
  border-radius: 20px;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #47822B;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-text {
  font-size: 13px;
  color: #47822B;
  font-weight: 600;
}

.current-time {
  font-size: 13px;
  color: #8a8aa3;
  font-family: 'SF Mono', Monaco, monospace;
}

.main-content {
  padding: 0;
  overflow-y: auto;
  height: calc(100vh - 64px);
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.2);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Element Plus Overrides - Light Theme */
.el-dialog {
  background: #ffffff !important;
  border-radius: 12px !important;
  border: 1px solid #e8e8ef;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}

.el-dialog__header {
  background: #f5f7fa;
  border-bottom: 1px solid #e8e8ef;
  padding: 16px 20px !important;
}

.el-dialog__title {
  color: #1a1a2e !important;
  font-weight: 600;
}

.el-dialog__body {
  color: #4a4a6a;
}

.el-switch__core {
  background: #e8e8ef !important;
  border: none !important;
}

.el-switch.is-checked .el-switch__core {
  background: #3979F6 !important;
}

.el-message {
  background: #ffffff !important;
  border: 1px solid #e8e8ef !important;
  border-radius: 8px !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.el-message__content {
  color: #1a1a2e !important;
}
</style>
