<script setup>
import { nextTick, ref } from 'vue'
import api from '../api'

const messages = ref([])        // {role:'user'|'ai', content, time}
const input = ref('')
const loading = ref(false)
const listEl = ref(null)

const suggestions = [
  '今天整体运营情况怎么样？',
  '目前有多少运单在运输中？',
  '车辆和司机的使用情况如何？',
  '有哪些异常运单需要处理？',
  '给我一份今日运营简报',
]

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// 行内 **粗体**
function inline(s) {
  return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
}

// 超轻量 Markdown：标题 / 列表 / 表格 / 段落
function renderMd(text) {
  const lines = text.split('\n')
  let html = ''
  let list = null      // 'ul' | null
  let table = false
  const closeList = () => { if (list) { html += `</${list}>`; list = null } }
  const closeTable = () => { if (table) { html += '</tbody></table>'; table = false } }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line) { closeList(); closeTable(); continue }
    if (/^#{1,6}\s/.test(line)) {                    // 标题
      closeList(); closeTable()
      html += `<h4>${inline(line.replace(/^#{1,6}\s*/, ''))}</h4>`
    } else if (/^[-*]\s+/.test(line)) {              // 无序列表
      closeTable()
      if (list !== 'ul') { closeList(); html += '<ul>'; list = 'ul' }
      html += `<li>${inline(line.replace(/^[-*]\s+/, ''))}</li>`
    } else if (/^\d+[.、]\s*/.test(line)) {          // 有序列表
      closeTable()
      if (list !== 'ol') { closeList(); html += '<ol>'; list = 'ol' }
      html += `<li>${inline(line.replace(/^\d+[.、]\s*/, ''))}</li>`
    } else if (/^\|.+\|/.test(line)) {               // 表格
      closeList()
      const cells = line.split('|').slice(1, -1).map((c) => c.trim())
      if (cells.every((c) => /^:?-{2,}:?$/.test(c))) continue   // 分隔行
      if (!table) { html += '<div class="md-table"><table><tbody>'; table = true }
      const tag = html.endsWith('</thead>') || i > 0 && lines[i - 1].includes('---') ? 'td' : 'td'
      html += '<tr>' + cells.map((c) => `<${tag}>${inline(c)}</${tag}>`).join('') + '</tr>'
    } else {                                          // 段落
      closeList(); closeTable()
      html += `<p>${inline(line)}</p>`
    }
  }
  closeList(); closeTable()
  return html
}

async function scrollBottom() {
  await nextTick()
  if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight
}

function now() {
  const d = new Date()
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function ask(q) {
  const question = (q || input.value).trim()
  if (!question || loading.value) return
  input.value = ''
  messages.value.push({ role: 'user', content: question, time: now() })
  loading.value = true
  await scrollBottom()

  try {
    const history = messages.value.slice(-7, -1).map((m) => ({
      role: m.role === 'ai' ? 'assistant' : 'user',
      content: m.content,
    }))
    const { answer } = await api.post('/ai/ask', { question, history }, { timeout: 60000 })
    messages.value.push({ role: 'ai', content: answer, time: now() })
  } catch (e) {
    messages.value.push({ role: 'ai', content: `请求失败：${e.message}`, time: now() })
  } finally {
    loading.value = false
    await scrollBottom()
  }
}
</script>

<template>
  <div class="ai-page">
    <div class="ai-hero">
      <div class="hero-icon">
        <svg viewBox="0 0 24 24" width="30" height="30" fill="none">
          <path d="M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 14.4 7.2 16.9l.9-5.4L4.2 7.7l5.4-.8L12 2z" fill="#fff" opacity=".9"/>
          <circle cx="12" cy="12" r="10.5" stroke="#fff" stroke-opacity=".5" stroke-width="1.4" fill="none"/>
        </svg>
      </div>
      <div>
        <h3>AI 智能助手</h3>
        <p>接入通义千问 · 实时掌握系统运单、车辆、司机与网点数据，直接用一句话提问</p>
      </div>
    </div>

    <div ref="listEl" class="chat-list">
      <div v-if="!messages.length" class="chat-welcome">
        <div class="hello">你好，我是物流 AI 助手 👋</div>
        <div class="sub">试试下面这些问题，或直接输入你想了解的内容</div>
        <div class="chips">
          <button v-for="s in suggestions" :key="s" class="chip" @click="ask(s)">{{ s }}</button>
        </div>
      </div>

      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="avatar" :class="m.role">
          <svg v-if="m.role === 'ai'" viewBox="0 0 24 24" width="18" height="18"><path d="M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 14.4 7.2 16.9l.9-5.4L4.2 7.7l5.4-.8L12 2z" fill="#6366f1"/></svg>
          <span v-else>我</span>
        </div>
        <div class="bubble" :class="m.role">
          <div v-if="m.role === 'ai'" class="md" v-html="renderMd(m.content)"></div>
          <template v-else>{{ m.content }}</template>
        </div>
        <span class="time">{{ m.time }}</span>
      </div>

      <div v-if="loading" class="msg ai">
        <div class="avatar ai">
          <svg viewBox="0 0 24 24" width="18" height="18"><path d="M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4L12 14.4 7.2 16.9l.9-5.4L4.2 7.7l5.4-.8L12 2z" fill="#6366f1"/></svg>
        </div>
        <div class="bubble ai typing">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <input
        v-model="input"
        placeholder="输入你的问题，例如：今天有多少运单待揽收？"
        @keyup.enter="ask()"
      />
      <button class="send" :disabled="loading || !input.trim()" @click="ask()">发送</button>
    </div>
  </div>
</template>

<style scoped>
.ai-page { display: flex; flex-direction: column; height: calc(100vh - 120px); min-height: 480px; }

.ai-hero {
  display: flex; align-items: center; gap: 14px;
  background: linear-gradient(120deg, #6366f1, #8b5cf6 55%, #a78bfa);
  border-radius: 12px; padding: 18px 22px; color: #fff; margin-bottom: 14px;
}
.hero-icon { width: 52px; height: 52px; border-radius: 14px; background: rgba(255,255,255,.18); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ai-hero h3 { margin: 0 0 4px; font-size: 17px; }
.ai-hero p { margin: 0; font-size: 13px; opacity: .9; }

.chat-list { flex: 1; overflow-y: auto; background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px; }

.chat-welcome { text-align: center; padding: 40px 10px 20px; }
.hello { font-size: 18px; font-weight: 700; }
.sub { color: var(--muted); font-size: 13px; margin: 8px 0 22px; }
.chips { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
.chip {
  border: 1px solid var(--line); background: #f8fafc; border-radius: 999px;
  padding: 8px 16px; font-size: 13px; cursor: pointer; transition: all .15s;
}
.chip:hover { border-color: var(--primary); color: var(--primary); background: #eef2ff; }

.msg { display: flex; align-items: flex-end; gap: 10px; margin-bottom: 16px; }
.msg.user { flex-direction: row-reverse; }
.avatar {
  width: 32px; height: 32px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600;
}
.avatar.ai { background: #eef2ff; }
.avatar.user { background: var(--primary); color: #fff; }

.bubble { max-width: 72%; padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.7; word-break: break-word; }
.bubble.ai { background: #f4f5fa; border: 1px solid var(--line); border-bottom-left-radius: 4px; }
.bubble.user { background: var(--primary); color: #fff; border-bottom-right-radius: 4px; }
.time { font-size: 11px; color: var(--muted); flex-shrink: 0; }

.bubble.typing { display: flex; gap: 5px; padding: 14px 16px; }
.bubble.typing span { width: 7px; height: 7px; border-radius: 50%; background: #a5b4fc; animation: blink 1.2s infinite; }
.bubble.typing span:nth-child(2) { animation-delay: .2s; }
.bubble.typing span:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0%, 60%, 100% { opacity: .3; transform: translateY(0); } 30% { opacity: 1; transform: translateY(-3px); } }

/* AI 回答的富文本排版 */
.md :deep(p) { margin: 4px 0; }
.md :deep(h4) { margin: 10px 0 6px; font-size: 14px; color: var(--primary); }
.md :deep(ul), .md :deep(ol) { margin: 4px 0; padding-left: 20px; }
.md :deep(li) { margin: 3px 0; }
.md :deep(strong) { color: var(--primary); }
.md :deep(.md-table) { margin: 8px 0; overflow-x: auto; }
.md :deep(table) { border-collapse: collapse; font-size: 13px; background: #fff; border-radius: 8px; overflow: hidden; }
.md :deep(td) { border: 1px solid var(--line); padding: 6px 12px; }
.md :deep(tr:first-child td) { background: #eef2ff; font-weight: 600; }

.chat-input { display: flex; gap: 10px; margin-top: 14px; }
.chat-input input {
  flex: 1; height: 44px; border: 1px solid var(--line); border-radius: 10px;
  padding: 0 16px; font-size: 14px; outline: none;
}
.chat-input input:focus { border-color: var(--primary); }
.send {
  height: 44px; padding: 0 26px; border: none; border-radius: 10px;
  background: var(--primary); color: #fff; font-size: 14px; cursor: pointer;
}
.send:disabled { opacity: .5; cursor: not-allowed; }
</style>
