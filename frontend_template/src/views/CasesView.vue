<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
import NuoAvatar from '../components/NuoAvatar.vue'
import { experiences } from '../data/experiences'
import { useUserStore } from '../stores/user'
const user = useUserStore(), cases = ref([]), search = ref(''), error = ref(''), loading = ref(true), page = ref(1), hasMore = ref(false)
async function load(reset = true) {
  loading.value = true; error.value = ''
  if (reset) page.value = 1
  try { const data = await api.get('/cases', { params: { q: search.value, page: page.value } }); cases.value = reset ? data : [...cases.value, ...data]; hasMore.value = data.length === 20 }
  catch(e) { error.value = e.message } finally { loading.value = false }
}
const recent=ref([]), recentLoading=ref(true), recentError=ref('')
async function loadRecent() { recentLoading.value=true;recentError.value='';try { recent.value=(await api.get('/conversations')).slice(0,3) } catch(e) { recentError.value=e.message } finally { recentLoading.value=false } }
function date(value) { return new Date(value + 'Z').toLocaleDateString('zh-CN') }
onMounted(()=>{load();loadRecent();user.loadProfile().catch(()=>{})})
</script>
<template>
<section class="workspace-hero"><div class="workspace-hero-copy"><span class="eyebrow">A SPACE FOR YOUR NEXT STEP</span><h1>你好，{{ user.profile?.nickname || '欢迎回来' }}<span class="title-dot">。</span><br>今天，也从容一点。</h1><p>把琐碎放在这里，把思路交给小诺。<br>聊聊想法，梳理案情，找到下一步。</p><div class="hero-actions"><RouterLink class="button primary" to="/assistant"><AppIcon name="chat" :size="18" />和小诺聊聊</RouterLink><RouterLink class="button" to="/cases/new"><AppIcon name="plus" :size="18" />新建案件</RouterLink></div></div><div class="hero-illustration"><span class="floating-note note-one"><AppIcon name="edit" :size="16" />灵感，慢慢展开</span><NuoAvatar /><span class="floating-note note-two"><AppIcon name="check" :size="16" />思路，一点点清晰</span><span class="hero-caption">YOUR EVERYDAY THINKING PARTNER</span></div></section>
<div class="workspace-pulse"><RouterLink to="/cases"><span class="pulse-icon sage"><AppIcon name="case" /></span><div><span>我的案件</span><strong>{{ user.profile?.case_count ?? '—' }} <small>件记录</small></strong></div><AppIcon name="arrow" :size="16" /></RouterLink><RouterLink to="/records"><span class="pulse-icon peach"><AppIcon name="chat" /></span><div><span>聊过的想法</span><strong>{{ user.profile?.conversation_count ?? '—' }} <small>段对话</small></strong></div><AppIcon name="arrow" :size="16" /></RouterLink><RouterLink to="/assistant?mode=case"><span class="pulse-icon lilac"><AppIcon name="spark" /></span><div><span>需要理清案情？</span><strong class="pulse-label">一起找找头绪</strong></div><AppIcon name="arrow" :size="16" /></RouterLink></div>
<div class="studio-section-title"><div><span class="eyebrow">MORE WAYS TO BEGIN</span><h2>不止一种打开方式</h2></div><RouterLink class="text-link" to="/assistant">发现小诺<AppIcon name="arrow" :size="16" /></RouterLink></div>
<div class="experience-grid home-experiences"><RouterLink v-for="experience in experiences" :key="experience.key" :to="{path:'/assistant',query:{topic:experience.key}}" class="experience-card" :class="experience.tone"><span class="experience-icon"><AppIcon :name="experience.icon" :size="23" /></span><strong>{{ experience.label }}</strong><span>{{ experience.subtitle }}</span><span class="experience-arrow" aria-hidden="true">↗</span></RouterLink></div>
<section class="recent-strip"><div><span class="eyebrow">PICK UP WHERE YOU LEFT OFF</span><h3>接着上次聊</h3></div><span v-if="recentLoading" class="muted small">正在读取对话…</span><span v-else-if="recentError" class="muted small">{{ recentError }} <button class="text-button" @click="loadRecent">重试</button></span><div v-else-if="recent.length" class="recent-links"><RouterLink v-for="row in recent" :key="row.id" :to="`/chat/${row.id}`"><AppIcon :name="row.case_id ? 'case' : 'chat'" :size="16" /><span>{{ row.title }}</span><span aria-hidden="true">↗</span></RouterLink></div><RouterLink v-else class="text-link" to="/assistant">第一段对话，从这里开始 ↗</RouterLink></section>
<div class="section-heading"><div><h2>我的案件 <span class="count">{{ cases.length }}{{ hasMore ? '+' : '' }}</span></h2><p>集中管理案情、材料与咨询记录</p></div><form class="search-box" @submit.prevent="load()"><AppIcon name="search" :size="18" /><input v-model="search" maxlength="100" placeholder="搜索案件名称或案情" aria-label="搜索案件" /><button :disabled="loading">搜索</button></form></div>
<p v-if="error" class="error" role="alert">{{ error }}</p><div v-if="loading && !cases.length" class="empty-state">正在读取案件…</div>
<div v-else-if="!cases.length" class="empty-state panel"><span class="empty-icon"><AppIcon name="case" :size="32" /></span><h3>{{ search ? '没有找到匹配的案件' : '从你的第一件案件开始' }}</h3><p>{{ search ? '换个关键词再试试。' : '记录案情和诉求，AI 将基于你提供的信息辅助梳理。' }}</p><RouterLink v-if="!search" class="button primary" to="/cases/new"><AppIcon name="plus" />新建案件</RouterLink></div>
<div v-else class="case-grid"><RouterLink v-for="item in cases" :key="item.id" :to="`/cases/${item.id}`" :data-category="item.category" class="case-card"><div class="case-card-top"><span class="case-type-icon"><AppIcon name="case" :size="23" /></span><span class="badge" :class="item.analysis ? 'green' : ''">{{ item.analysis ? '已整理' : '待整理' }}</span></div><span class="case-category">{{ item.category }} · {{ item.stage }}</span><h3>{{ item.title }}</h3><p class="case-excerpt">{{ item.description }}</p><div class="case-card-bottom"><span>更新于 {{ date(item.updated_at) }}</span><span class="text-link">查看案件 <AppIcon name="arrow" :size="16" /></span></div></RouterLink><RouterLink to="/cases/new" class="new-case-card"><span class="empty-icon"><AppIcon name="plus" :size="28" /></span><strong>添加新的案件</strong><span>记录事实，开始梳理</span></RouterLink></div>
<button v-if="hasMore" class="button load-more" :disabled="loading" @click="page++;load(false)">加载更多案件</button><div class="tip-strip"><AppIcon name="shield" /><span>建议先使用脱敏信息。AI 依据当前案件记录辅助整理，生成内容请逐项核实。</span></div></template>
