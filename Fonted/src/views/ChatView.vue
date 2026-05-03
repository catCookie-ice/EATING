<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores'

const router = useRouter()
const auth = useAuthStore()

interface Message {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

const messages = ref<Message[]>([])
const inputMessage = ref('')
const isStreaming = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)

// 检查是否已登录
const isLoggedIn = computed(() => auth.isLoggedIn)

// 初始化欢迎消息
onMounted(() => {
  messages.value.push({
    role: 'assistant',
    content: '你好！我是 EATING AI 助手，可以帮你推荐食谱、搭配食材、解答美食相关问题。有什么想问的吗？',
  })
})

// 发送消息
async function sendMessage() {
  if (!inputMessage.value.trim() || isStreaming.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''

  // 添加用户消息
  messages.value.push({ role: 'user', content: userMessage })
  messages.value.push({ role: 'assistant', content: '', isStreaming: true })
  isStreaming.value = true

  await nextTick()
  scrollToBottom()

  try {
    // 构建消息历史
    const chatMessages = messages.value
      .filter(m => !m.isStreaming)
      .map(m => ({ role: m.role, content: m.content }))

    // 添加当前用户消息
    chatMessages.push({ role: 'user', content: userMessage })

    // 使用 fetch 处理 SSE
    const res = await fetch('/api/chat/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${auth.token}`
      },
      body: JSON.stringify({
        messages: chatMessages,
        temperature: 0.7,
        max_tokens: 2048
      })
    })

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }

    const reader = res.body?.getReader()
    if (!reader) {
      throw new Error('无法读取响应')
    }

    const decoder = new TextDecoder()
    let done = false

    while (!done) {
      const { value, done: doneReading } = await reader.read()
      done = doneReading

      if (value) {
        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              done = true
              break
            }
            if (data) {
              const lastMsg = messages.value[messages.value.length - 1]
              lastMsg.content += data
              await nextTick()
              scrollToBottom()
            }
          }
        }
      }
    }
  } catch (error: any) {
    console.error('Chat error:', error)
    const lastMsg = messages.value[messages.value.length - 1]
    lastMsg.content = error.message || '抱歉，发送失败了，请稍后重试'
  } finally {
    isStreaming.value = false
    const lastMsg = messages.value[messages.value.length - 1]
    if (lastMsg) lastMsg.isStreaming = false
  }
}

// 滚动到底部
function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 回车发送
function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// 渲染 Markdown 链接为可点击的 HTML（新标签页打开）
function renderMarkdown(text: string): string {
  if (!text) return ''
  // 先转义 HTML 特殊字符防止 XSS
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  // 转换 Markdown 链接 [text](url) 为 <a> 标签（新标签页打开）
  html = html.replace(
    /\[([^\]]+)\]\((\/[^)]+)\)/g,
    '<a href="$2" class="recipe-link" target="_blank" rel="noopener">$1</a>'
  )
  // 转换换行为 <br>
  html = html.replace(/\n/g, '<br>')
  return html
}

// 返回首页
function goBack() {
  router.push('/')
}
</script>

<template>
  <div class="chat-view">
    <div class="chat-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <h1>EATING AI 助手</h1>
      <div class="header-spacer"></div>
    </div>

    <div v-if="!isLoggedIn" class="login-prompt">
      <p>请先 <router-link to="/login">登录</router-link> 后再使用 AI 聊天</p>
    </div>

    <div v-else class="chat-container">
      <div ref="messagesContainer" class="messages">
        <div
          v-for="(msg, index) in messages"
          :key="index"
          class="message"
          :class="msg.role"
        >
          <div class="message-avatar">
            {{ msg.role === 'user' ? '👤' : '🍽️' }}
          </div>
          <div class="message-content">
            <div
              v-if="msg.role === 'assistant'"
              class="markdown-body"
              :class="{ streaming: msg.isStreaming }"
              v-html="renderMarkdown(msg.content)"
            ></div>
            <pre v-else :class="{ streaming: msg.isStreaming }">{{ msg.content || (msg.isStreaming ? '...' : '') }}</pre>
          </div>
        </div>
      </div>

      <div class="input-area">
        <textarea
          v-model="inputMessage"
          placeholder="输入你的问题..."
          @keydown="handleKeydown"
          :disabled="isStreaming"
          rows="1"
        ></textarea>
        <button
          class="send-btn"
          @click="sendMessage"
          :disabled="!inputMessage.trim() || isStreaming"
        >
          {{ isStreaming ? '...' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 180px);
  max-width: 800px;
  margin: 0 auto;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  padding: 1rem 0;
  gap: 1rem;
}

.back-btn {
  background: none;
  border: 1px solid #4caf50;
  color: #4caf50;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-btn:hover {
  background: #4caf50;
  color: white;
}

.chat-header h1 {
  color: #2e7d32;
  font-size: 1.3rem;
  flex: 1;
  text-align: center;
}

.header-spacer {
  width: 60px;
}

.login-prompt {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-prompt a {
  color: #4caf50;
  font-weight: 600;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.messages {
  flex: 1;
  min-height: 200px;
  overflow-y: auto;
  padding: 1rem;
}

.message {
  display: flex;
  gap: 0.8rem;
  margin-bottom: 1rem;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e8f5e9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #e3f2fd;
}

.message-content {
  flex: 1;
  max-width: 80%;
}

.message-content pre {
  margin: 0;
  padding: 0.8rem 1rem;
  border-radius: 12px;
  background: #f5f5f5;
  color: #333;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.5;
}

.message.user .message-content pre {
  background: #e8f5e9;
}

.message-content pre.streaming {
  animation: pulse 1s infinite;
}

.message-content .markdown-body {
  margin: 0;
  padding: 0.8rem 1rem;
  border-radius: 12px;
  background: #f5f5f5;
  color: #333;
  font-size: 0.95rem;
  line-height: 1.7;
  word-wrap: break-word;
  overflow-x: auto;
}

.message-content .markdown-body.streaming {
  animation: pulse 1s infinite;
}

.recipe-link {
  color: #2e7d32;
  font-weight: 600;
  text-decoration: none;
  border-bottom: 2px solid #81c784;
  transition: all 0.2s ease;
  padding: 0 2px;
}

.recipe-link:hover {
  color: #1b5e20;
  border-bottom-color: #2e7d32;
  background: #e8f5e9;
  border-radius: 3px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.input-area {
  display: flex;
  gap: 0.8rem;
  padding: 1rem;
  border-top: 1px solid #eee;
  align-items: flex-end;
}

.input-area textarea {
  flex: 1;
  padding: 0.8rem 1rem;
  border: 1px solid #ddd;
  border-radius: 20px;
  resize: none;
  font-family: inherit;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.3s ease;
  min-height: 44px;
  max-height: 120px;
  overflow-y: auto;
  word-break: break-word;
}

.input-area textarea:focus {
  border-color: #4caf50;
}

.send-btn {
  background: #4caf50;
  color: white;
  border: none;
  padding: 0.8rem 1.5rem;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.send-btn:hover:not(:disabled) {
  background: #43a047;
}

.send-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .chat-view {
    height: calc(100vh - 120px);
  }

  .message-content {
    max-width: 90%;
  }
}
</style>