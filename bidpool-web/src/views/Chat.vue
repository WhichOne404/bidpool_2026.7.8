<template>
  <div class="lb-page chat-page">
    <!-- 左侧会话列表 -->
    <div class="lb-widget sessions-panel">
      <div class="sessions-header">
        <h2>会话历史</h2>
        <button class="lb-btn lb-btn-success btn-sm" @click="createNewSession">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新建
        </button>
      </div>
      <div class="sessions-list">
        <div v-if="!sessions.length" class="empty-sessions">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          <p>暂无会话</p>
          <button class="lb-btn lb-btn-primary" @click="createNewSession">开始对话</button>
        </div>
        <div
          v-for="session in sessions"
          :key="session.id"
          :class="['session-item', { active: currentSessionId === session.id }]"
          @click="switchSession(session.id)"
        >
          <div class="session-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div class="session-info">
            <div class="session-title">{{ session.title || '新会话' }}</div>
            <div class="session-time">{{ formatTime(session.timestamp) }}</div>
          </div>
          <button class="lb-btn lb-btn-danger btn-sm" @click.stop="deleteSession(session.id)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 右侧聊天区域 -->
    <div class="chat-area">
      <!-- 聊天头部 -->
      <div class="lb-widget chat-header">
        <div class="header-info">
          <div class="header-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2a5 5 0 0 1 5 5v2a5 5 0 0 1-10 0V7a5 5 0 0 1 5-5z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="22"/>
            </svg>
          </div>
          <div class="header-text">
            <h3>AI 智能助手</h3>
            <span class="header-status">
              <span class="status-dot"></span>
              在线
            </span>
          </div>
        </div>
        <div class="header-actions">
          <button class="lb-btn lb-btn-ghost" @click="clearCurrentChat">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
            清空
          </button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div class="messages-container" ref="messagesRef">
        <div v-if="!currentMessages.length" class="welcome-screen">
          <div class="welcome-icon">
            <svg viewBox="0 0 100 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="50" cy="40" r="35" fill="rgba(71, 130, 43, .2)"/>
              <circle cx="50" cy="40" r="25" fill="rgba(71, 130, 43, .3)"/>
              <circle cx="50" cy="40" r="15" fill="rgba(71, 130, 43, .4)"/>
              <path d="M42 40 L48 46 L58 36" stroke="#47822B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h2>欢迎使用智能助手</h2>
          <p>我可以帮你管理标讯、发送通知、查询数据</p>
          <div class="quick-actions">
            <button class="lb-btn lb-btn-ghost" @click="executeCommand('收集今天的标讯')">收集标讯</button>
            <button class="lb-btn lb-btn-ghost" @click="executeCommand('发送标讯到钉钉')">发送到钉钉</button>
            <button class="lb-btn lb-btn-ghost" @click="executeCommand('查看任务状态')">任务状态</button>
          </div>
        </div>

        <div v-for="(msg, idx) in currentMessages" :key="idx" :class="['message', msg.type]">
          <div class="message-avatar">
            <div v-if="msg.type === 'user'" class="avatar user">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
            </div>
            <div v-else class="avatar assistant">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a5 5 0 0 1 5 5v2a5 5 0 0 1-10 0V7a5 5 0 0 1 5-5z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="22"/>
              </svg>
            </div>
          </div>
          <div class="message-content">
            <div class="message-text" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>

        <div v-if="sending" class="message assistant">
          <div class="message-avatar">
            <div class="avatar assistant">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2a5 5 0 0 1 5 5v2a5 5 0 0 1-10 0V7a5 5 0 0 1 5-5z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="22"/>
              </svg>
            </div>
          </div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="lb-widget input-area">
        <div class="input-wrapper">
          <textarea
            v-model="inputMessage"
            placeholder="输入消息，Ctrl + Enter 发送..."
            @keydown.enter.ctrl="sendMessage"
            rows="1"
            ref="textareaRef"
            @input="autoResize"
          ></textarea>
          <button class="lb-btn lb-btn-primary send-btn" @click="sendMessage" :disabled="!inputMessage.trim() || sending">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { chatApi } from '../api'
import { marked } from 'marked'

const SESSIONS_KEY = 'bidpool_sessions'

marked.setOptions({ breaks: true, gfm: true })

const sessions = ref([])
const currentSessionId = ref('')
const inputMessage = ref('')
const sending = ref(false)
const messagesRef = ref(null)
const textareaRef = ref(null)

const currentMessages = computed(() => {
  const session = sessions.value.find(s => s.id === currentSessionId.value)
  return session ? session.messages : []
})

const renderMarkdown = (content) => {
  if (!content) return ''
  return marked.parse(content)
}

const generateSessionId = () => 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)

const loadSessions = () => {
  try {
    const saved = localStorage.getItem(SESSIONS_KEY)
    if (saved) {
      sessions.value = JSON.parse(saved)
      if (sessions.value.length > 0) {
        currentSessionId.value = sessions.value[0].id
      }
    }
  } catch (error) {
    console.error('加载会话失败:', error)
  }
}

const saveSessions = () => {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.value))
  } catch (error) {
    console.error('保存会话失败:', error)
  }
}

const createNewSession = () => {
  const newSession = {
    id: generateSessionId(),
    title: '新会话',
    messages: [],
    timestamp: Date.now()
  }
  sessions.value.unshift(newSession)
  currentSessionId.value = newSession.id
  saveSessions()
}

const switchSession = (sessionId) => {
  currentSessionId.value = sessionId
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const deleteSession = async (sessionId) => {
  try {
    await ElMessageBox.confirm('删除该对话？', '提示', { type: 'warning' })
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    if (currentSessionId.value === sessionId) {
      currentSessionId.value = sessions.value.length > 0 ? sessions.value[0].id : ''
    }
    saveSessions()
  } catch (e) {}
}

const clearCurrentChat = () => {
  const session = sessions.value.find(s => s.id === currentSessionId.value)
  if (session) {
    session.messages = []
    saveSessions()
  }
}

const addMessage = (content, type = 'user') => {
  const session = sessions.value.find(s => s.id === currentSessionId.value)
  if (!session) return

  session.messages.push({ id: Date.now(), content, type })
  session.timestamp = Date.now()

  if (type === 'user' && session.messages.filter(m => m.type === 'user').length === 1) {
    session.title = content.slice(0, 15) + (content.length > 15 ? '...' : '')
  }

  saveSessions()
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return
  if (!currentSessionId.value) createNewSession()

  const message = inputMessage.value.trim()
  inputMessage.value = ''
  if (textareaRef.value) textareaRef.value.style.height = 'auto'

  addMessage(message, 'user')
  sending.value = true

  try {
    const res = await chatApi.send(message, currentSessionId.value)
    if (res.code === 0) {
      addMessage(res.data.response, 'assistant')
    } else {
      addMessage('处理失败: ' + res.message, 'assistant')
    }
  } catch (error) {
    addMessage('网络错误，请稍后重试', 'assistant')
  } finally {
    sending.value = false
  }
}

const executeCommand = (cmd) => {
  inputMessage.value = cmd
  sendMessage()
}

const autoResize = () => {
  if (textareaRef.value) {
    textareaRef.value.style.height = 'auto'
    textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 150) + 'px'
  }
}

const formatTime = (ts) => {
  if (!ts) return ''
  const date = new Date(ts)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前'
  if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前'
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadSessions()
})
</script>

<style scoped lang="scss">
@import '@/styles/light-blue.scss';

.chat-page {
  display: flex;
  height: calc(100vh - 64px);
  padding: 0;
  background: var(--lb-body-bg);
}

/* 左侧会话列表 */
.sessions-panel {
  width: 280px;
  margin-bottom: 0;
  border-radius: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid $lb-border;
}

.sessions-header {
  padding: 1.25rem;
  border-bottom: 1px solid $lb-border;
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--lb-text-primary);
    margin: 0;
  }
}

.sessions-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.empty-sessions {
  text-align: center;
  padding: 40px 20px;
  color: var(--lb-text-muted);

  svg {
    opacity: 0.4;
  }

  p {
    margin: 12px 0 16px;
    font-size: 0.875rem;
    color: var(--lb-text-muted);
  }
}

.session-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: 4px;

  &:hover {
    background: $lb-bg-page;
  }

  &.active {
    background: rgba($lb-green, .15);
  }
}

.session-icon {
  width: 36px;
  height: 36px;
  background: $lb-bg-page;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $lb-text-muted;
  flex-shrink: 0;

  svg {
    width: 18px;
    height: 18px;
  }
}

.session-item.active .session-icon {
  background: rgba($lb-green, .2);
  color: $lb-green;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--lb-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  font-size: 0.75rem;
  color: var(--lb-text-muted);
  margin-top: 2px;
}

.btn-sm {
  padding: 6px;

  svg {
    width: 14px;
    height: 14px;
  }
}

/* 右侧聊天区域 */
.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 聊天头部 */
.chat-header {
  margin-bottom: 0;
  border-radius: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  width: 40px;
  height: 40px;
  background: rgba($lb-green, .15);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: $lb-green;

  svg {
    width: 20px;
    height: 20px;
  }
}

.header-text h3 {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--lb-text-primary);
  margin: 0 0 2px;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: $lb-green;
}

.status-dot {
  width: 6px;
  height: 6px;
  background: $lb-green;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

/* 消息列表 */
.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome-screen {
  text-align: center;
  padding: 60px 24px;
}

.welcome-icon {
  width: 120px;
  margin: 0 auto 24px;

  svg {
    width: 100%;
    height: auto;
  }
}

.welcome-screen h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--lb-text-primary);
  margin: 0 0 8px;
}

.welcome-screen p {
  font-size: 0.875rem;
  color: var(--lb-text-muted);
  margin: 0 0 32px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
}

/* 消息样式 */
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 800px;
  margin-left: auto;
  margin-right: auto;

  &.user {
    flex-direction: row-reverse;
  }
}

.message-avatar {
  flex-shrink: 0;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 18px;
    height: 18px;
  }

  &.user {
    background: $lb-blue;
    color: white;
  }

  &.assistant {
    background: rgba($lb-green, .15);
    color: $lb-green;
  }
}

.message-content {
  max-width: 70%;
}

.message-text {
  padding: 14px 18px;
  border-radius: 16px;
  font-size: 0.875rem;
  line-height: 1.6;
}

.message.user .message-text {
  background: $lb-green;
  color: white;
  border-bottom-right-radius: 4px;
}

.message.assistant .message-text {
  background: $lb-bg-page;
  color: $lb-text-secondary;
  border-bottom-left-radius: 4px;
}

.message-text :deep(p) {
  margin: 0 0 8px;

  &:last-child {
    margin-bottom: 0;
  }
}

.message-text :deep(ul), .message-text :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.message-text :deep(li) {
  margin: 4px 0;
}

.message-text :deep(code) {
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.8125rem;
}

.message-text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 0.8125rem;
}

.message-text :deep(th), .message-text :deep(td) {
  padding: 8px 12px;
  border: 1px solid $lb-border;
  text-align: left;
}

.message-text :deep(th) {
  background: $lb-bg-page;
  font-weight: 600;
}

.message-text :deep(h3) {
  font-size: 0.9375rem;
  margin: 12px 0 8px;
  color: var(--lb-text-primary);
}

.message-text :deep(strong) {
  font-weight: 600;
  color: var(--lb-text-primary);
}

/* 打字动画 */
.typing-indicator {
  display: flex;
  gap: 6px;
  padding: 16px 20px;
  background: $lb-bg-page;
  border-radius: 16px;

  span {
    width: 8px;
    height: 8px;
    background: $lb-green;
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out;

    &:nth-child(1) { animation-delay: 0s; }
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-8px); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 输入区域 */
.input-area {
  margin-bottom: 0;
  border-radius: 0;
  padding: 16px 24px 24px;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 12px 16px;
  background: $lb-bg-page;
  border: 1px solid $lb-border;
  border-radius: 16px;
  max-width: 800px;
  margin: 0 auto;

  textarea {
    flex: 1;
    border: none;
    outline: none;
    font-size: 0.875rem;
    color: $lb-text-primary;
    resize: none;
    max-height: 120px;
    line-height: 1.5;
    background: transparent;
    font-family: $lb-font-family;

    &::placeholder {
      color: $lb-text-muted;
    }
  }
}

.send-btn {
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 10px;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .chat-page {
    flex-direction: column;
  }

  .sessions-panel {
    width: 100%;
    height: auto;
    max-height: 200px;
    border-right: none;
    border-bottom: 1px solid $lb-border;
  }
}
</style>