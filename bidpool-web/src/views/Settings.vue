<template>
  <div class="lb-page settings-page">
    <!-- 页面标题 -->
    <h1 class="lb-page-title">
      系统设置
      <small>配置平台账号、LLM和钉钉群</small>
    </h1>

    <div class="settings-grid">
      <!-- 平台配置 -->
      <div class="lb-widget settings-card">
        <div class="card-header">
          <div class="header-icon platform">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
            </svg>
          </div>
          <div class="header-text">
            <h3>平台账号</h3>
            <p>配置标讯平台登录信息</p>
          </div>
        </div>
        <div class="card-body">
          <div class="form-group">
            <label class="lb-label">千里马账号</label>
            <input type="text" v-model="platform.qianlima.username" placeholder="输入用户名" class="lb-input" />
          </div>
          <div class="form-group">
            <label class="lb-label">千里马密码</label>
            <input type="password" v-model="platform.qianlima.password" placeholder="输入密码" class="lb-input" />
          </div>
          <div class="form-actions">
            <button class="lb-btn lb-btn-primary" @click="save" :disabled="saving">
              <svg v-if="saving" class="spinner" viewBox="0 0 24 24" width="16" height="16">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none" stroke-dasharray="60" stroke-dashoffset="20"/>
              </svg>
              {{ saving ? '保存中...' : '保存配置' }}
            </button>
          </div>
        </div>
      </div>

      <!-- LLM配置 -->
      <div class="lb-widget settings-card">
        <div class="card-header">
          <div class="header-icon llm">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2a5 5 0 0 1 5 5v2a5 5 0 0 1-10 0V7a5 5 0 0 1 5-5z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="22"/>
            </svg>
          </div>
          <div class="header-text">
            <h3>LLM 配置</h3>
            <p>配置大语言模型接口</p>
          </div>
        </div>
        <div class="card-body">
          <div class="form-group">
            <label class="lb-label">API 地址</label>
            <input type="text" v-model="llm.api_base" placeholder="https://api.example.com/v1" class="lb-input" />
          </div>
          <div class="form-group">
            <label class="lb-label">模型选择</label>
            <select v-model="llm.model" class="lb-select">
              <option value="">请选择模型</option>
              <option value="gpt-4o">GPT-4o</option>
              <option value="gpt-3.5-turbo">GPT-3.5</option>
              <option value="glm-5">GLM-5</option>
              <option value="claude-3-opus">Claude 3 Opus</option>
            </select>
          </div>
          <div class="form-group">
            <label class="lb-label">API Key</label>
            <input type="password" v-model="llm.api_key" placeholder="sk-..." class="lb-input" />
          </div>
          <div class="form-actions">
            <button class="lb-btn lb-btn-primary" @click="save" :disabled="saving">保存配置</button>
            <button class="lb-btn lb-btn-ghost" @click="testLLM" :disabled="testing">
              {{ testing ? '测试中...' : '测试连接' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 钉钉配置 -->
      <div class="lb-widget settings-card full">
        <div class="card-header">
          <div class="header-icon dingtalk">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div class="header-text">
            <h3>钉钉群配置</h3>
            <p>配置消息推送的钉钉群</p>
          </div>
          <button class="lb-btn lb-btn-success" @click="addGroup">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            添加群
          </button>
        </div>
        <div class="card-body">
          <div v-if="!dingtalk.length" class="empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <p>暂未配置钉钉群</p>
            <button class="lb-btn lb-btn-primary" @click="addGroup">添加钉钉群</button>
          </div>

          <div v-else class="groups-list">
            <div v-for="(g, i) in dingtalk" :key="i" class="lb-widget group-card">
              <div class="group-header">
                <span class="group-index">{{ i + 1 }}</span>
                <span class="group-name">{{ g.name || '未命名群' }}</span>
                <button class="lb-btn lb-btn-danger btn-sm" @click="dingtalk.splice(i, 1)">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
              <div class="group-fields">
                <div class="field">
                  <label>群名称</label>
                  <input type="text" v-model="g.name" placeholder="输入群名称" class="lb-input" />
                </div>
                <div class="field">
                  <label>Webhook URL</label>
                  <input type="text" v-model="g.webhook_url" placeholder="https://oapi.dingtalk.com/robot/send?access_token=..." class="lb-input" />
                </div>
                <div class="field">
                  <label>匹配行业 <small>(可选，用于自动路由)</small></label>
                  <div class="industry-tags">
                    <span
                      v-for="ind in industries"
                      :key="ind"
                      :class="['tag', { active: g.industries?.includes(ind) }]"
                      @click="toggleIndustry(g, ind)"
                    >
                      {{ ind }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="dingtalk.length" class="card-footer">
            <button class="lb-btn lb-btn-primary" @click="save" :disabled="saving">保存全部</button>
            <button class="lb-btn lb-btn-ghost" @click="testDingtalk" :disabled="testingWebhook">
              {{ testingWebhook ? '测试中...' : '测试 Webhook' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const industries = ['政府', '医疗', '金融', '教育', '通信', '能源', '企业', '其他']

const saving = ref(false)
const testing = ref(false)
const testingWebhook = ref(false)

const platform = reactive({ qianlima: { username: '', password: '' } })
const llm = reactive({ api_base: 'https://aiapi.chaitin.net/v1', api_key: '', model: 'glm-5' })
const dingtalk = ref([])

const load = async () => {
  try {
    const res = await axios.get('/api/v1/config')
    if (res.data.code === 0) {
      const d = res.data.data
      if (d.platforms?.qianlima) {
        platform.qianlima.username = d.platforms.qianlima.username
        if (!d.platforms.qianlima.password?.includes('****')) platform.qianlima.password = d.platforms.qianlima.password
      }
      dingtalk.value = d.dingtalk_groups || []
      if (d.llm) {
        llm.api_base = d.llm.api_base || ''
        llm.api_key = d.llm.api_key || ''
        llm.model = d.llm.model || ''
      }
    }
  } catch {}
}

const save = async () => {
  saving.value = true
  try {
    await axios.post('/api/v1/config', {
      platforms: platform,
      dingtalk_groups: dingtalk.value.filter(g => g.name && g.webhook_url),
      llm
    })
    ElMessage.success('保存成功')
    load()
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

const testLLM = async () => {
  testing.value = true
  try {
    const res = await axios.post('/chat/', { message: '你好' })
    ElMessage.success(res.data.code === 0 ? '连接正常' : '连接失败')
  } catch { ElMessage.error('连接失败') }
  finally { testing.value = false }
}

const testDingtalk = async () => {
  const g = dingtalk.value.find(g => g.webhook_url)
  if (!g) { ElMessage.warning('请先配置 Webhook'); return }
  testingWebhook.value = true
  try {
    const res = await axios.post('/api/v1/config/dingtalk/test', { webhook_url: g.webhook_url })
    ElMessage.success(res.data.code === 0 ? '测试成功' : '测试失败')
  } catch { ElMessage.error('测试失败') }
  finally { testingWebhook.value = false }
}

const addGroup = () => {
  dingtalk.value.push({ name: '', webhook_url: '', industries: [] })
}

const toggleIndustry = (group, industry) => {
  if (!group.industries) group.industries = []
  const idx = group.industries.indexOf(industry)
  if (idx > -1) {
    group.industries.splice(idx, 1)
  } else {
    group.industries.push(industry)
  }
}

onMounted(load)
</script>

<style scoped lang="scss">
@import '@/styles/light-blue.scss';

.settings-page {
  padding: $lb-content-padding;
}

/* 设置网格 */
.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $lb-grid-gutter;
}

/* 设置卡片 */
.settings-card {
  margin-bottom: 0;
}

.settings-card.full {
  grid-column: span 2;
}

.card-header {
  padding: 1.25rem;
  border-bottom: 1px solid $lb-border;
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  svg {
    width: 24px;
    height: 24px;
  }

  &.platform {
    background: rgba($lb-orange, .15);
    color: $lb-orange;
  }

  &.llm {
    background: rgba($lb-blue, .15);
    color: $lb-blue;
  }

  &.dingtalk {
    background: rgba($lb-green, .15);
    color: $lb-green;
  }
}

.header-text {
  flex: 1;

  h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--lb-text-primary);
    margin: 0 0 2px;
  }

  p {
    font-size: 0.8125rem;
    color: var(--lb-text-muted);
    margin: 0;
  }
}

.card-body {
  padding: 1.25rem;
}

.card-footer {
  padding: 1rem 1.25rem;
  border-top: 1px solid $lb-border;
  display: flex;
  gap: 12px;
  background: $lb-bg-page;
}

/* 表单 */
.form-group {
  margin-bottom: 20px;

  &:last-of-type {
    margin-bottom: 0;
  }
}

.form-actions {
  margin-top: 24px;
  display: flex;
  gap: 12px;
}

/* 小按钮 */
.btn-sm {
  padding: 6px;

  svg {
    width: 14px;
    height: 14px;
  }
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--lb-text-muted);

  svg {
    opacity: 0.4;
    margin-bottom: 16px;
  }

  p {
    font-size: 0.9375rem;
    color: var(--lb-text-muted);
    margin: 0 0 20px;
  }
}

/* 群列表 */
.groups-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.group-card {
  background: $lb-bg-page;
  margin-bottom: 0;
}

.group-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: $lb-bg-widget;
  border-bottom: 1px solid $lb-border;
}

.group-index {
  width: 24px;
  height: 24px;
  background: $lb-green;
  color: white;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 600;
}

.group-name {
  flex: 1;
  font-weight: 600;
  color: var(--lb-text-primary);
}

.group-fields {
  padding: 16px;
}

.field {
  margin-bottom: 16px;

  &:last-child {
    margin-bottom: 0;
  }

  label {
    display: block;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--lb-text-muted);
    margin-bottom: 8px;

    small {
      font-weight: 400;
      color: $lb-text-muted;
    }
  }
}

/* 行业标签 */
.industry-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  padding: 6px 14px;
  background: $lb-bg-page;
  border: 1px solid $lb-border;
  border-radius: 6px;
  font-size: 0.8125rem;
  color: var(--lb-text-secondary);
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: $lb-border;
  }

  &.active {
    background: $lb-green;
    border-color: $lb-green;
    color: white;
  }
}

/* 动画 */
.spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 响应式 */
@media (max-width: 1200px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }

  .settings-card.full {
    grid-column: span 1;
  }
}
</style>