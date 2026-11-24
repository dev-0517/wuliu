<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
import NuoAvatar from '../components/NuoAvatar.vue'
import { experiences } from '../data/experiences'
const route=useRoute(), router=useRouter(), cases=ref([]), error=ref(''), loading=ref(true), busy=ref(false), q=ref(''), mode=ref(route.query.mode==='case' ? 'case' : 'general')
const topic=experiences.find(item=>item.key===route.query.topic)
const draft=ref(topic?.prompt || ''), group=ref(0)
const topicGroups=[['聊聊今天的心情','帮我安排一份学习计划','帮我把一段话写得更清楚'],['给我一个周末放松的灵感','帮我把复杂问题拆成小步骤','一起练习一次自我介绍'],['用一个例子解释新知识','帮我写一封有礼貌的邮件','帮我整理今天的待办']]
const ideaInput=ref(null)
async function pickExperience(item) { draft.value=item.prompt;await nextTick();ideaInput.value?.focus() }

async function load() { loading.value=true;error.value='';try { cases.value=await api.get('/cases',{params:{q:q.value}}) } catch(e) { error.value=e.message } finally { loading.value=false } }
onMounted(load)
async function start(item=null, prompt='') {
  if(busy.value) return
  busy.value=true;error.value=''
  try { const c=await api.post('/conversations',item ? {case_id:item.id} : {});router.push({path:`/chat/${c.id}`,query:prompt ? {prompt} : {}}) }
  catch(e) { error.value=e.message } finally { busy.value=false }
}
</script>
<template>
  <div class="assistant-intro studio-intro"><div><span class="eyebrow">A LITTLE CLARITY, EVERY DAY</span><h1>你好，我是小诺<span class="title-dot">。</span></h1><p>给想法一点空间，让事情慢慢清晰。<br>聊日常、找灵感，也一起理清案情。</p><span class="intro-note"><span />你的日常思考搭子</span></div><NuoAvatar /></div>
  <div class="assistant-modes" aria-label="选择对话模式"><button :class="{selected:mode==='general'}" :aria-pressed="mode==='general'" @click="mode='general'"><AppIcon name="chat" /><span><strong>日常聊天</strong><small>写作、学习、计划，或者随便聊聊</small></span></button><button :class="{selected:mode==='case'}" :aria-pressed="mode==='case'" @click="mode='case'"><AppIcon name="case" /><span><strong>案件咨询</strong><small>结合自己的案情和材料深入讨论</small></span></button></div>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <section v-if="mode==='general'" class="general-studio">
    <div class="panel general-starter"><div class="starter-heading"><span class="badge">从一个想法开始</span><span class="small muted">不必先创建案件</span></div><h2>想到什么，就聊什么。</h2><p>一个问题、一段文字，或今天发生的小事。小诺都愿意听。</p><form class="idea-composer" @submit.prevent="start(null,draft.trim())"><textarea ref="ideaInput" v-model="draft" rows="2" maxlength="4000" aria-label="想聊的话题" placeholder="今天，有什么想和小诺聊聊？" /><div><span class="small muted">想好再发送，进入对话后还可以修改</span><button class="button primary" :disabled="busy"><AppIcon name="arrow" :size="18" />{{ busy ? '正在创建…' : '开始聊天' }}</button></div></form><div class="topic-header"><span>试试这些话题</span><button class="text-button" type="button" @click="group=(group+1)%topicGroups.length">换一组 ↻</button></div><div class="topic-chips"><button v-for="suggestion in topicGroups[group]" :key="suggestion" :disabled="busy" @click="draft=suggestion">{{ suggestion }}<span aria-hidden="true">↗</span></button></div></div>
    <div class="studio-section-title"><div><span class="eyebrow">A LITTLE INSPIRATION</span><h2>今天，一起做点什么？</h2></div><span class="muted small">选择一个方向，打开思路</span></div>
    <div class="experience-grid"><button v-for="experience in experiences" :key="experience.key" class="experience-card" :class="experience.tone" @click="pickExperience(experience)"><span class="experience-icon"><AppIcon :name="experience.icon" :size="24" /></span><strong>{{ experience.label }}</strong><span>{{ experience.subtitle }}</span><span class="experience-arrow" aria-hidden="true">↗</span></button></div>
    <p class="small muted studio-privacy">日常聊天不读取案件与材料；需要结合具体案情时，切换到“案件咨询”。</p>
  </section>
  <section v-else class="panel assistant-picker"><div class="section-heading"><div><h2>从哪个案件开始？</h2><p>回答前查询这个案件的记录，保留来源，方便核对</p></div><RouterLink class="button" to="/cases/new"><AppIcon name="plus" :size="17" />新建案件</RouterLink></div><form class="search-box" @submit.prevent="load"><AppIcon name="search" :size="18" /><input v-model="q" maxlength="100" placeholder="搜索要咨询的案件" aria-label="搜索案件" /><button :disabled="loading">搜索</button></form><p v-if="loading" class="empty-state">正在读取案件…</p><div v-else-if="!cases.length" class="empty-state"><h3>{{ q ? '没有匹配的案件' : '先记录一件案件' }}</h3><p>写下事情经过，就能结合具体情况辅助整理。</p><RouterLink v-if="!q" class="button" to="/cases/new">记录案件</RouterLink></div><button v-for="item in cases" :key="item.id" class="picker-row" :disabled="busy" @click="start(item)"><span class="case-type-icon"><AppIcon name="case" /></span><span><strong>{{ item.title }}</strong><small>{{ item.category }} · {{ item.stage }}</small></span><AppIcon name="arrow" :size="18" /></button></section>
  <p class="center muted small">AI 内容可能存在错误，请核实重要信息。</p>
</template>
