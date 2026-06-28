<template>
  <div class="lb-page api-docs-page">
    <h1 class="lb-page-title">
      API 文档
      <small>查看系统接口说明</small>
    </h1>

    <!-- 搜索 -->
    <div class="search-bar">
      <input type="text" v-model="searchKeyword" placeholder="搜索接口..." class="lb-input" />
    </div>

    <!-- API 分类 -->
    <div class="api-sections">
      <div class="api-section" v-for="section in filteredSections" :key="section.name">
        <div class="section-header">
          <h2>{{ section.name }}</h2>
          <span class="api-count">{{ section.apis.length }} 个接口</span>
        </div>

        <div class="api-list">
          <div class="api-item" v-for="api in section.apis" :key="api.path">
            <div class="api-header">
              <span :class="['method-badge', api.method.toLowerCase()]">{{ api.method }}</span>
              <code class="api-path">{{ api.path }}</code>
            </div>
            <div class="api-desc">{{ api.description }}</div>
            <div class="api-details" v-if="api.params || api.response">
              <div class="params-section" v-if="api.params">
                <h4>参数</h4>
                <table class="params-table">
                  <thead>
                    <tr>
                      <th>字段</th>
                      <th>类型</th>
                      <th>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="param in api.params" :key="param.field">
                      <td><code>{{ param.field }}</code></td>
                      <td>{{ param.type }}</td>
                      <td>{{ param.desc }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="response-section" v-if="api.response">
                <h4>响应示例</h4>
                <pre class="response-code">{{ api.response }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 用户信息 -->
    <div class="user-info-section">
      <div class="lb-widget">
        <h3>当前登录信息</h3>
        <div class="info-row">
          <span class="label">用户名</span>
          <span class="value">{{ currentUser }}</span>
        </div>
        <div class="info-row">
          <span class="label">登录时间</span>
          <span class="value">{{ loginTime }}</span>
        </div>
        <button class="lb-btn lb-btn-danger" @click="logout">退出登录</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const searchKeyword = ref('')
const currentUser = ref('')
const loginTime = ref('')

// 获取登录信息
const authData = sessionStorage.getItem('auth')
if (authData) {
  const auth = JSON.parse(authData)
  currentUser.value = auth.username
  loginTime.value = new Date(auth.loginTime).toLocaleString('zh-CN')
}

// API 文档数据
const sections = ref([
  {
    name: '任务管理',
    apis: [
      {
        method: 'POST',
        path: '/api/v1/tasks',
        description: '创建新任务',
        params: [
          { field: 'name', type: 'string', desc: '任务名称' },
          { field: 'task_type', type: 'string', desc: '任务类型：crawl(收集)/send(发送)' },
          { field: 'cron_expr', type: 'string', desc: '定时表达式（可选）' },
          { field: 'enabled', type: 'boolean', desc: '是否启用' }
        ],
        response: '{"code": 0, "data": {...}, "message": "创建成功"}'
      },
      {
        method: 'GET',
        path: '/api/v1/tasks',
        description: '获取任务列表',
        response: '{"code": 0, "data": [...], "total": 10}'
      },
      {
        method: 'GET',
        path: '/api/v1/tasks/:id',
        description: '获取任务详情'
      },
      {
        method: 'PUT',
        path: '/api/v1/tasks/:id',
        description: '更新任务',
        params: [
          { field: 'enabled', type: 'boolean', desc: '是否启用' },
          { field: 'cron_expr', type: 'string', desc: '定时表达式' }
        ]
      },
      {
        method: 'DELETE',
        path: '/api/v1/tasks/:id',
        description: '删除任务'
      },
      {
        method: 'POST',
        path: '/api/v1/tasks/:id/run',
        description: '手动执行任务'
      },
      {
        method: 'POST',
        path: '/api/v1/tasks/batch-delete',
        description: '批量删除任务',
        params: [
          { field: 'ids', type: 'array', desc: '任务ID数组' }
        ]
      }
    ]
  },
  {
    name: '标讯管理',
    apis: [
      {
        method: 'GET',
        path: '/api/v1/bids',
        description: '获取标讯列表',
        params: [
          { field: 'page', type: 'int', desc: '页码' },
          { field: 'page_size', type: 'int', desc: '每页数量' },
          { field: 'keyword', type: 'string', desc: '搜索关键词' }
        ]
      },
      {
        method: 'GET',
        path: '/api/v1/bids/:id',
        description: '获取标讯详情'
      },
      {
        method: 'DELETE',
        path: '/api/v1/bids/:id',
        description: '删除标讯'
      },
      {
        method: 'POST',
        path: '/api/v1/bids/batch-delete',
        description: '批量删除标讯',
        params: [
          { field: 'ids', type: 'array', desc: '标讯ID数组' }
        ]
      },
      {
        method: 'POST',
        path: '/api/v1/bids/dispatch',
        description: '发送标讯到钉钉',
        params: [
          { field: 'ids', type: 'array', desc: '标讯ID数组' },
          { field: 'webhook_url', type: 'string', desc: '钉钉群webhook地址' }
        ]
      }
    ]
  },
  {
    name: '智能对话',
    apis: [
      {
        method: 'POST',
        path: '/api/v1/chat',
        description: '智能对话接口',
        params: [
          { field: 'message', type: 'string', desc: '用户消息' },
          { field: 'session_id', type: 'string', desc: '会话ID' }
        ],
        response: '{"code": 0, "data": {"response": "...", "session_id": "..."}}'
      }
    ]
  },
  {
    name: '系统状态',
    apis: [
      {
        method: 'GET',
        path: '/api/v1/status',
        description: '获取系统状态',
        response: '{"code": 0, "data": {"bid_count": 100, "task_count": 5, ...}}'
      },
      {
        method: 'GET',
        path: '/api/v1/config',
        description: '获取系统配置'
      },
      {
        method: 'POST',
        path: '/api/v1/config',
        description: '保存系统配置'
      }
    ]
  }
])

const filteredSections = computed(() => {
  if (!searchKeyword.value) return sections.value

  return sections.value.map(section => {
    const filteredApis = section.apis.filter(api =>
      api.path.toLowerCase().includes(searchKeyword.value.toLowerCase()) ||
      api.description.toLowerCase().includes(searchKeyword.value.toLowerCase())
    )
    return { ...section, apis: filteredApis }
  }).filter(section => section.apis.length > 0)
})

const logout = () => {
  sessionStorage.removeItem('auth')
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<style scoped lang="scss">
@import '@/styles/light-blue.scss';

.api-docs-page {
  padding: $lb-content-padding;
  max-width: 1200px;
}

.search-bar {
  margin-bottom: 20px;

  .lb-input {
    width: 100%;
    max-width: 400px;
  }
}

.api-sections {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.api-section {
  .lb-widget {
    margin-bottom: 0;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid $lb-border-light;

    h2 {
      font-size: 1rem;
      font-weight: 600;
      color: var(--lb-text-primary);
      margin: 0;
    }

    .api-count {
      font-size: 0.75rem;
      color: var(--lb-text-muted);
      background: $lb-bg-page;
      padding: 4px 8px;
      border-radius: 12px;
    }
  }
}

.api-list {
  padding: 16px 20px;
}

.api-item {
  padding: 12px 0;
  border-bottom: 1px solid $lb-border-light;

  &:last-child {
    border-bottom: none;
  }
}

.api-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.method-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;

  &.get { background: #e3f2fd; color: #1976d2; }
  &.post { background: #e8f5e9; color: #388e3c; }
  &.put { background: #fff3e0; color: #f57c00; }
  &.delete { background: #ffebee; color: #d32f2f; }
}

.api-path {
  background: $lb-bg-page;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.875rem;
  color: var(--lb-text-secondary);
}

.api-desc {
  font-size: 0.875rem;
  color: var(--lb-text-muted);
}

.api-details {
  margin-top: 12px;
  padding: 12px;
  background: $lb-bg-page;
  border-radius: 8px;
}

.params-section, .response-section {
  h4 {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--lb-text-muted);
    margin: 0 0 8px;
  }
}

.params-table {
  width: 100%;
  border-collapse: collapse;

  th, td {
    padding: 8px;
    text-align: left;
    border-bottom: 1px solid $lb-border-light;
    font-size: 0.75rem;
  }

  th {
    color: var(--lb-text-muted);
  }

  td code {
    background: white;
    padding: 2px 6px;
    border-radius: 4px;
  }
}

.response-code {
  background: white;
  padding: 12px;
  border-radius: 8px;
  font-size: 0.75rem;
  overflow-x: auto;
  white-space: pre-wrap;
}

.user-info-section {
  margin-top: 30px;

  .lb-widget {
    padding: 20px;
  }

  h3 {
    font-size: 1rem;
    font-weight: 600;
    margin: 0 0 16px;
  }

  .info-row {
    display: flex;
    margin-bottom: 12px;

    .label {
      width: 100px;
      color: var(--lb-text-muted);
      font-size: 0.875rem;
    }

    .value {
      color: var(--lb-text-primary);
      font-weight: 600;
    }
  }
}
</style>