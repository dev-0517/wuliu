<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
import MarkdownText from '../components/MarkdownText.vue'
import SourceList from '../components/SourceList.vue'
const route=useRoute(), conversation=ref(null), messages=ref([]), item=ref(null), input=ref(''), error=ref(''), notice=ref(''), busy=ref(false), loading=ref(true), bottom=ref(null), pending=ref('')
const isCase=computed(()=>conversation.value?.case_id != null)
const suggestions=computed(()=>isCase.value ? ['请帮我梳理目前的案件事实，并标出来源','我还需要补充哪些信息？请先问最关键的三个问题','根据已录入情况，下一步可以做什么？'] : ['今天有点累，想找人聊聊','帮我安排一份学习计划','帮我把一段话写得更清楚'])
async function scroll() { await nextTick();bottom.value?.scrollIntoView({behavior:'smooth',block:'end'}) }
onMounted(async () => {
  try {
    const data=await api.get(`/conversations/${route.params.id}`);conversation.value=data.conversation;messages.value=data.messages
    if(isCase.value) item.value=await api.get(`/cases/${conversation.value.case_id}`)
    if(typeof route.query.prompt==='string') input.value=route.query.prompt.slice(0,4000)
    await scroll()
  } catch(e) { error.value=e.message } finally { loading.value=false }
})
async function send() {
  const content=input.value.trim();if(!content || busy.value || !conversation.value) return
  busy.value=true;pending.value=content;error.value='';notice.value='';await scroll()
  try { const data=await api.post(`/conversations/${conversation.value.id}/messages`,{content});messages.value.push(data.question,data.reply);conversation.value.title=data.title || conversation.value.title;input.value='';await scroll() }
  catch(e) { error.value=e.message } finally { busy.value=false;pending.value='';await scroll() }
}
function choose(text) { input.value=text }
function keyboard(event) { if(event.key==='Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault();send() } }
async function copy(text) { try { await navigator.clipboard.writeText(text);notice.value='回答已复制' } catch { error.value='复制失败，请手动选择文本复制' } }
</script>
<template>
  <div class="chat-workspace"><div class="chat-heading"><div><h2>{{ isCase ? '案件问答' : '和小诺聊聊' }} <span class="badge">{{ isCase ? '案件咨询' : '日常聊天' }}</span></h2><p class="conversation-title">{{ conversation?.title || '正在读取对话…' }}</p></div><RouterLink v-if="item" class="button" :to="`/cases/${item.id}`"><AppIcon name="case" :size="17" />查看案件</RouterLink><RouterLink v-else class="button" to="/assistant"><AppIcon name="plus" :size="17" />新对话</RouterLink></div>
    <div v-if="item" class="context-card"><AppIcon name="case" /><div><strong>{{ item.title }}</strong><span>{{ item.category }} · {{ item.stage }} · 回答前查询记录，来源可展开核对</span></div><span class="context-dot" /></div>
    <div v-else-if="conversation" class="general-context"><AppIcon name="chat" :size="16" />聊日常、聊想法，也可以一起解决问题。</div>
    <div class="chat-messages" aria-live="polite"><p v-if="loading" class="empty-state">正在读取聊天记录…</p>
      <div v-else-if="!messages.length && !busy && conversation" class="chat-welcome"><span class="assistant-symbol"><AppIcon name="spark" :size="30" /></span><h2>{{ isCase ? '我们从哪一步开始？' : '很高兴和你聊聊。' }}</h2><p>{{ isCase ? '我会先查询这个案件的记录，再结合你的问题辅助梳理。' : '有一个想法、一个问题，或者只是想聊聊天，都可以。' }}<br>{{ isCase ? '信息不足时，我会提出具体追问。' : '从下面选一个话题，或直接输入你想说的话。' }}</p><div class="suggestion-list"><button v-for="s in suggestions" :key="s" @click="choose(s)">{{ s }}<AppIcon name="arrow" :size="16" /></button></div></div>
      <article v-for="m in messages" :key="m.id" class="message" :class="m.role"><span class="message-avatar"><AppIcon :name="m.role==='assistant' ? 'spark' : 'user'" :size="18" /></span><div class="message-body"><span class="message-label">{{ m.role==='assistant' ? '小诺' : '你' }}</span><div class="message-bubble"><MarkdownText v-if="m.role === 'assistant'" :content="m.content" /><div v-else class="preserve">{{ m.content }}</div></div><SourceList v-if="m.role==='assistant'" :sources="m.sources || []" /><button v-if="m.role==='assistant'" class="text-button small" @click="copy(m.content)">复制回答</button></div></article>
      <template v-if="busy"><article class="message user"><span class="message-avatar"><AppIcon name="user" :size="18" /></span><div class="message-body"><span class="message-label">你</span><div class="message-bubble preserve">{{ pending }}</div></div></article><div class="message assistant"><span class="message-avatar"><AppIcon name="spark" :size="18" /></span><div class="message-bubble thinking" role="status"><span /><span /><span />{{ isCase ? '正在查阅案件并整理回答…' : '小诺正在回复…' }}</div></div></template><div ref="bottom" />
    </div>
    <div class="composer-area"><div v-if="error" class="error" role="alert">{{ error }} <button v-if="input.trim() && !busy && conversation" class="text-button" @click="send">重试发送</button></div><p v-if="notice" class="success small" role="status">{{ notice }}</p><form class="composer" @submit.prevent="send"><textarea v-model="input" :disabled="busy || !conversation" maxlength="4000" rows="2" aria-label="咨询问题" :placeholder="isCase ? '描述你的问题，或补充案情…' : '和小诺说点什么…'" @keydown="keyboard" /><div class="composer-bottom"><span>Enter 发送 · Shift + Enter 换行</span><button class="send-button" :disabled="busy || !input.trim() || !conversation" aria-label="发送问题"><AppIcon name="send" :size="19" /></button></div></form><p class="small muted center">{{ isCase ? 'AI 内容仅供参考，重要事实和法律依据请核实。' : 'AI 内容可能存在错误，请核实重要信息。' }}</p></div>
  </div>
</template>
