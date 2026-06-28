<template>
  <div class="lb-page dashboard-page">
    <!-- Page Title -->
    <h1 class="lb-page-title">
      Analytics <small>标讯平台运行概况</small>
    </h1>

    <!-- Stats Cards Row -->
    <div class="stats-row">
      <div class="lb-widget stat-widget">
        <div class="stat-content">
          <h2 class="stat-value">{{ status.bid_count || 0 }}</h2>
          <div class="stat-details">
            <div class="stat-item">
              <h6>+{{ status.today_count || 0 }}</h6>
              <p>今日新增</p>
            </div>
            <div class="stat-item">
              <h6>{{ status.pending_count || 0 }}</h6>
              <p>待发送</p>
            </div>
            <div class="stat-item">
              <h6>{{ status.success_rate || 0 }}%</h6>
              <p>成功率</p>
            </div>
          </div>
        </div>
        <div class="stat-icon success">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </div>
      </div>

      <div class="lb-widget stat-widget">
        <div class="stat-content">
          <h2 class="stat-value">{{ status.task_count || 0 }}</h2>
          <div class="stat-details">
            <div class="stat-item">
              <h6>{{ status.active_jobs?.length || 0 }}</h6>
              <p>运行中</p>
            </div>
            <div class="stat-item">
              <h6>{{ status.enabled_count || 0 }}</h6>
              <p>已启用</p>
            </div>
          </div>
        </div>
        <div class="stat-icon info">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
        </div>
      </div>

      <div class="lb-widget stat-widget">
        <div class="stat-content">
          <h2 class="stat-value">{{ status.message_count || 0 }}</h2>
          <div class="stat-details">
            <div class="stat-item">
              <h6>{{ status.today_sent || 0 }}</h6>
              <p>今日发送</p>
            </div>
            <div class="stat-item">
              <h6>{{ status.group_count || 0 }}</h6>
              <p>钉钉群</p>
            </div>
          </div>
        </div>
        <div class="stat-icon warning">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </div>
      </div>

      <div class="lb-widget stat-widget">
        <div class="stat-content">
          <h2 class="stat-value">{{ formatDuration(status.uptime || 0) }}</h2>
          <div class="stat-details">
            <div class="stat-item">
              <h6>{{ status.server_time?.split(' ')[0] || '-' }}</h6>
              <p>运行日期</p>
            </div>
          </div>
        </div>
        <div class="stat-icon primary">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
      </div>
    </div>

    <!-- Main Chart Area -->
    <div class="lb-widget chart-widget">
      <div class="widget-header">
        <h5>标讯趋势 <span class="sub-title">近7日数据</span></h5>
        <div class="widget-controls">
          <button class="refresh-btn" @click="refreshStatus">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="lb-widget-body">
        <div class="chart-container" v-if="trendData.length > 0">
          <svg viewBox="0 0 800 240" class="trend-chart">
            <!-- Grid lines -->
            <line x1="50" y1="20" x2="50" y2="180" stroke="#e8e8ef" stroke-width="1"/>
            <line x1="50" y1="180" x2="750" y2="180" stroke="#e8e8ef" stroke-width="1"/>
            <line x1="50" y1="100" x2="750" y2="100" stroke="#f0f0f5" stroke-width="1" stroke-dasharray="4"/>

            <!-- Y-axis labels -->
            <text x="40" y="185" fill="#8a8aa3" font-size="11" text-anchor="end">0</text>
            <text x="40" y="105" fill="#8a8aa3" font-size="11" text-anchor="end">{{ maxCount }}</text>
            <text x="40" y="25" fill="#8a8aa3" font-size="11" text-anchor="end">{{ maxCount * 2 }}</text>

            <!-- Gradient definition -->
            <defs>
              <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#3979F6" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="#3979F6" stop-opacity="0"/>
              </linearGradient>
            </defs>

            <!-- Area fill -->
            <path :d="areaPath" fill="url(#chartGradient)"/>

            <!-- Line -->
            <path :d="linePath" stroke="#3979F6" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>

            <!-- Data points -->
            <circle v-for="(point, i) in chartPoints" :key="i" :cx="point.x" :cy="point.y" r="5" fill="#3979F6" stroke="white" stroke-width="2"/>

            <!-- X-axis labels -->
            <text v-for="(label, i) in trendDates" :key="i" :x="50 + i * 100" y="200" fill="#8a8aa3" font-size="11" text-anchor="middle">{{ label }}</text>

            <!-- Value labels -->
            <text v-for="(point, i) in chartPoints" :key="'v'+i" :x="point.x" :y="point.y - 12" fill="#3979F6" font-size="11" font-weight="600" text-anchor="middle">{{ trendData[i]?.count || 0 }}</text>
          </svg>
        </div>
        <div class="chart-empty" v-else>
          <p>暂无数据</p>
        </div>
      </div>
    </div>

    <!-- Big Stats Row -->
    <div class="big-stats-row">
      <div class="lb-widget big-stat-widget">
        <div class="big-stat-header">
          <h5>行业分布</h5>
          <span class="lb-badge lb-badge-success">实时</span>
        </div>
        <div class="lb-widget-body">
          <div class="progress-group">
            <div class="progress-item">
              <span class="progress-label">政府</span>
              <div class="lb-progress">
                <div class="lb-progress-bar lb-progress-info" style="width: 45%"></div>
              </div>
              <span class="progress-value">45%</span>
            </div>
            <div class="progress-item">
              <span class="progress-label">医疗</span>
              <div class="lb-progress">
                <div class="lb-progress-bar lb-progress-info" style="width: 30%"></div>
              </div>
              <span class="progress-value">30%</span>
            </div>
            <div class="progress-item">
              <span class="progress-label">金融</span>
              <div class="lb-progress">
                <div class="lb-progress-bar lb-progress-info" style="width: 15%"></div>
              </div>
              <span class="progress-value">15%</span>
            </div>
            <div class="progress-item">
              <span class="progress-label">其他</span>
              <div class="lb-progress">
                <div class="lb-progress-bar lb-progress-info" style="width: 10%"></div>
              </div>
              <span class="progress-value">10%</span>
            </div>
          </div>
        </div>
      </div>

      <div class="lb-widget big-stat-widget">
        <div class="big-stat-header">
          <h5>地区分布</h5>
          <span class="lb-badge lb-badge-info">西南</span>
        </div>
        <div class="lb-widget-body">
          <div class="progress-group">
            <div class="progress-item">
              <span class="progress-label">重庆</span>
              <div class="lb-progress">
                <div class="lb-progress-bar lb-progress-warning" style="width: 55%"></div>
              </div>
              <span class="progress-value">55%</span>
            </div>
            <div class="progress-item">
              <span class="progress-label">四川</span>
              <div class="lb-progress">
                <div class="lb-progress-bar lb-progress-warning" style="width: 25%"></div>
              </div>
              <span class="progress-value">25%</span>
            </div>
            <div class="progress-item">
              <span class="progress-label">云南</span>
              <div class="lb-progress">
                <div class="lb-progress-bar lb-progress-warning" style="width: 12%"></div>
              </div>
              <span class="progress-value">12%</span>
            </div>
            <div class="progress-item">
              <span class="progress-label">其他</span>
              <div class="lb-progress">
                <div class="lb-progress-bar lb-progress-warning" style="width: 8%"></div>
              </div>
              <span class="progress-value">8%</span>
            </div>
          </div>
        </div>
      </div>

      <div class="lb-widget big-stat-widget">
        <div class="big-stat-header">
          <h5>任务状态</h5>
          <span class="lb-badge lb-badge-warning">监控</span>
        </div>
        <div class="lb-widget-body">
          <div class="task-status-grid">
            <div class="task-status-item">
              <div class="status-icon running">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
              </div>
              <div class="status-info">
                <div class="status-value">{{ status.active_jobs?.length || 0 }}</div>
                <div class="status-label">运行中</div>
              </div>
            </div>
            <div class="task-status-item">
              <div class="status-icon success">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                  <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
              </div>
              <div class="status-info">
                <div class="status-value">{{ successCount }}</div>
                <div class="status-label">已完成</div>
              </div>
            </div>
            <div class="task-status-item">
              <div class="status-icon pending">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
              </div>
              <div class="status-info">
                <div class="status-value">{{ status.task_count || 0 }}</div>
                <div class="status-label">总任务</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Activity Table -->
    <div class="lb-widget table-widget">
      <div class="widget-header">
        <h5>最近活动 <span class="sub-title">执行日志</span></h5>
        <span class="lb-badge lb-badge-primary">{{ status.recent_logs?.length || 0 }} 条</span>
      </div>
      <div class="lb-widget-body p-0">
        <table class="lb-table activity-table">
          <thead>
            <tr>
              <th>任务ID</th>
              <th>状态</th>
              <th>标讯数</th>
              <th>执行时间</th>
              <th>消息</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!status.recent_logs?.length">
              <td colspan="5" class="empty-cell">
                <div class="empty-state">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
                    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                    <line x1="16" y1="2" x2="16" y2="6"/>
                    <line x1="8" y1="2" x2="8" y2="6"/>
                    <line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                  <p>暂无活动记录</p>
                </div>
              </td>
            </tr>
            <tr v-for="(log, i) in status.recent_logs?.slice(0, 10)" :key="i">
              <td><code>{{ log.task_id?.slice(0, 8) }}...</code></td>
              <td>
                <span :class="['lb-badge', log.status === 'success' ? 'lb-badge-success' : log.status === 'failed' ? 'lb-badge-danger' : 'lb-badge-warning']">
                  {{ getStatusText(log.status) }}
                </span>
              </td>
              <td>{{ log.bids_count || 0 }}</td>
              <td class="time-cell">{{ formatTime(log.started_at) }}</td>
              <td class="message-cell">{{ log.message || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions-section">
      <h5 class="section-title">快速操作</h5>
      <div class="lb-actions-grid">
        <div class="lb-action-card" @click="goToTasks">
          <div class="lb-action-icon lb-action-icon-success">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="16"/>
              <line x1="8" y1="12" x2="16" y2="12"/>
            </svg>
          </div>
          <div>
            <span class="lb-action-title">创建任务</span>
            <span class="lb-action-desc">配置标讯收集任务</span>
          </div>
        </div>
        <div class="lb-action-card" @click="goToBids">
          <div class="lb-action-icon lb-action-icon-info">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <div>
            <span class="lb-action-title">标讯列表</span>
            <span class="lb-action-desc">查看收集的标讯</span>
          </div>
        </div>
        <div class="lb-action-card" @click="goToChat">
          <div class="lb-action-icon lb-action-icon-warning">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div>
            <span class="lb-action-title">智能对话</span>
            <span class="lb-action-desc">AI助手帮助</span>
          </div>
        </div>
        <div class="lb-action-card" @click="goToSettings">
          <div class="lb-action-icon lb-action-icon-primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </div>
          <div>
            <span class="lb-action-title">系统设置</span>
            <span class="lb-action-desc">配置平台参数</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { statusApi } from '../api'
import axios from 'axios'

const router = useRouter()
const status = ref({})
const trendData = ref([])
const trendDates = ref([])

const successCount = computed(() => {
  const logs = status.value.recent_logs || []
  return logs.filter(l => l.status === 'success').length
})

// 计算图表最大值
const maxCount = computed(() => {
  const max = Math.max(...trendData.value.map(d => d.count), 1)
  return Math.ceil(max / 10) * 10 || 10
})

// 计算图表坐标点
const chartPoints = computed(() => {
  const data = trendData.value
  if (data.length === 0) return []

  const max = maxCount.value
  return data.map((d, i) => ({
    x: 50 + i * 100,
    y: 180 - (d.count / max) * 160
  }))
})

// 生成线条路径
const linePath = computed(() => {
  if (chartPoints.value.length === 0) return ''
  return chartPoints.value.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
})

// 生成区域填充路径
const areaPath = computed(() => {
  if (chartPoints.value.length === 0) return ''
  const points = chartPoints.value
  const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
  return `${line} L ${points[points.length - 1].x} 180 L ${points[0].x} 180 Z`
})

const fetchStatus = async () => {
  try {
    const res = await statusApi.get()
    if (res.code === 0) status.value = res.data
  } catch (e) { console.error(e) }
}

const fetchTrend = async () => {
  try {
    const res = await axios.get('/api/v1/trend')
    if (res.data.code === 0) {
      trendData.value = res.data.data.stats || []
      trendDates.value = res.data.data.dates || []
    }
  } catch (e) { console.error(e) }
}

const refreshStatus = () => {
  fetchStatus()
  fetchTrend()
}

const goToTasks = () => router.push('/tasks')
const goToChat = () => router.push('/chat')
const goToBids = () => router.push('/bids')
const goToSettings = () => router.push('/settings')

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN', { hour12: false })
}

const formatDuration = (seconds) => {
  if (!seconds) return '0s'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

const getStatusText = (status) => {
  const map = { running: '运行中', success: '已完成', failed: '失败' }
  return map[status] || '未知'
}

onMounted(() => {
  fetchStatus()
  fetchTrend()
})
</script>

<style scoped lang="scss">
@import '@/styles/light-blue.scss';

.dashboard-page {
  padding: $lb-content-padding;
}

/* Stats Row */
.stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: $lb-grid-gutter;
  margin-bottom: $lb-grid-gutter;
}

.stat-widget {
  flex: 1;
  min-width: 240px;
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: $lb-text-primary;
  margin: 0;
}

.stat-details {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  margin-top: 0.75rem;
}

.stat-item {
  h6 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: $lb-text-secondary;
  }

  p {
    margin: 0;
    font-size: 0.75rem;
    color: $lb-text-muted;
  }
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  svg {
    width: 22px;
    height: 22px;
  }

  &.success { background: rgba($lb-success, .1); color: $lb-success; }
  &.info { background: rgba($lb-info, .1); color: $lb-info; }
  &.warning { background: rgba($lb-warning, .1); color: $lb-warning; }
  &.primary { background: rgba($lb-primary, .1); color: $lb-primary; }
}

/* Chart Widget */
.chart-widget {
  margin-bottom: $lb-grid-gutter;
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;

  h5 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: $lb-text-primary;

    .sub-title {
      font-weight: 400;
      color: $lb-text-muted;
    }
  }
}

.widget-controls {
  display: flex;
  gap: 8px;
}

.refresh-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: $lb-bg-page;
  border: 1px solid $lb-border;
  color: $lb-text-muted;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: $lb-border;
    color: $lb-text-primary;
  }
}

.chart-container {
  width: 100%;
}

.chart-empty {
  padding: 2rem;
  text-align: center;
  color: $lb-text-muted;
}

.trend-chart {
  width: 100%;
  height: auto;
}

/* Big Stats Row */
.big-stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: $lb-grid-gutter;
  margin-bottom: $lb-grid-gutter;
}

.big-stat-widget {
  flex: 1;
  min-width: 300px;
  margin-bottom: 0;
}

.big-stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;

  h5 {
    margin: 0;
    font-size: 0.875rem;
    font-weight: 600;
    color: $lb-text-primary;
  }
}

.progress-group {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.progress-item {
  display: flex;
  align-items: center;
  gap: 1rem;

  .lb-progress {
    flex: 1;
    margin-bottom: 0;
  }
}

.progress-label {
  min-width: 60px;
  font-size: 0.875rem;
  color: $lb-text-secondary;
}

.progress-value {
  min-width: 40px;
  font-size: 0.75rem;
  font-weight: 600;
  color: $lb-text-secondary;
  text-align: right;
}

/* Task Status Grid */
.task-status-grid {
  display: flex;
  gap: 1rem;
}

.task-status-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: $lb-bg-page;
  border-radius: 8px;
}

.status-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 18px;
    height: 18px;
  }

  &.running { background: rgba($lb-warning, .1); color: $lb-warning; }
  &.success { background: rgba($lb-success, .1); color: $lb-success; }
  &.pending { background: rgba($lb-primary, .1); color: $lb-primary; }
}

.status-info {
  .status-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: $lb-text-primary;
  }

  .status-label {
    font-size: 0.75rem;
    color: $lb-text-muted;
  }
}

/* Table Widget */
.table-widget {
  margin-bottom: $lb-grid-gutter;
}

.lb-widget-body.p-0 {
  padding: 0 !important;
}

.activity-table {
  code {
    background: $lb-bg-page;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    color: $lb-text-secondary;
    font-family: 'SF Mono', Monaco, monospace;
  }
}

.time-cell {
  font-size: 0.813rem;
  color: $lb-text-muted;
}

.message-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: $lb-text-muted;
}

.empty-cell {
  padding: 3rem !important;
  text-align: center;
}

.empty-state {
  p {
    margin-top: 1rem;
    font-size: 0.875rem;
    color: $lb-text-muted;
  }
}

/* Quick Actions */
.quick-actions-section {
  margin-bottom: 1.5rem;
}

.section-title {
  margin: 0 0 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: $lb-text-primary;
}

/* Responsive */
@media (max-width: 1200px) {
  .stats-row { flex-wrap: wrap; }
  .stat-widget { min-width: calc(50% - 12px); }
  .big-stats-row { flex-wrap: wrap; }
  .big-stat-widget { min-width: calc(50% - 12px); }
}

@media (max-width: 768px) {
  .dashboard-page { padding: 1rem; }
  .stats-row { flex-direction: column; }
  .stat-widget { min-width: 100%; }
  .big-stats-row { flex-direction: column; }
  .big-stat-widget { min-width: 100%; }
  .task-status-grid { flex-wrap: wrap; }
}
</style>