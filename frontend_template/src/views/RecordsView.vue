<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
const rows=ref([]), period=ref('all'), mode=ref('all'), q=ref(''), error=ref(''), loading=ref(false), page=ref(1), hasMore=ref(false), editing=ref(null), title=ref(''), saving=ref(false)
const filters=[{value:'all',label:'全部'},{value:'week',label:'近 7 天'},{value:'month',label:'近 30 天'},{value:'halfyear',label:'近半年'}]
async function load(reset=true) { loading.value=true;error.value='';if(reset) page.value=1;try { const data=await api.get('/conversations',{params:{period:period.value,mode:mode.value,q:q.value,page:page.value}});rows.value=reset ? data : [...rows.value,...data];hasMore.value=data.length===20 } catch(e) { error.value=e.message } finally { loading.value=false } }
async function remove(row) { if(!window.confirm('删除此会话及其中的全部消息？')) return;try { await api.delete(`/conversations/${row.id}`);await load() } catch(e) { error.value=e.message } }
function rename(row) { editing.value=row.id;title.value=row.title }
async function saveTitle() { if(!title.value.trim() || saving.value) return;saving.value=true;try { await api.patch(`/conversations/${editing.value}`,{title:title.value});editing.value=null;await load() } catch(e) { error.value=e.message } finally { saving.value=false } }
function date(value) { return new Date(value.endsWith('Z') ? value : value+'Z').toLocaleString('zh-CN',{hour12:false}) }
onMounted(()=>load())
</script>
<template>
  <div class="page-heading"><span class="eyebrow">CONVERSATION HISTORY</span><h1>每一次交流，都有记录。</h1><p>日常聊天与案件咨询，随时回来继续。</p></div>
  <div class="record-tools"><form class="search-box" @submit.prevent="load()"><AppIcon name="search" :size="18" /><input v-model="q" aria-label="搜索聊天记录" maxlength="100" placeholder="搜索标题或聊天内容" /><button :disabled="loading">搜索</button></form><label class="mode-filter">对话类型<select v-model="mode" aria-label="对话类型" :disabled="loading" @change="load()"><option value="all">全部对话</option><option value="general">日常聊天</option><option value="case">案件咨询</option></select></label></div>
  <div class="tabs"><button v-for="f in filters" :key="f.value" :disabled="loading" :class="{selected:period===f.value}" @click="period=f.value;load()">{{ f.label }}</button></div>
  <p v-if="error" class="error" role="alert">{{ error }}</p><div class="panel"><p v-if="loading && !rows.length" class="empty-state">正在读取记录…</p><div v-else-if="!rows.length" class="empty-state"><span class="empty-icon"><AppIcon name="history" :size="32" /></span><h3>暂无匹配的对话</h3><p>可以换个搜索词，或和小诺开始一段新对话。</p><RouterLink class="button primary" to="/assistant">开始对话<AppIcon name="arrow" :size="17" /></RouterLink></div>
    <div v-for="row in rows" :key="row.id" class="record-row"><span class="case-type-icon"><AppIcon :name="row.case_id == null ? 'chat' : 'case'" /></span><RouterLink :to="`/chat/${row.id}`" class="record-info"><h3>{{ row.title }}</h3><p><span class="badge">{{ row.case_id == null ? '日常聊天' : '案件咨询' }}</span> 最近更新 {{ date(row.updated_at) }}</p></RouterLink><RouterLink :to="`/chat/${row.id}`" class="text-link">继续聊天<AppIcon name="arrow" :size="16" /></RouterLink><button class="icon-button" @click="rename(row)" aria-label="修改会话标题"><AppIcon name="edit" :size="18" /></button><button class="icon-button danger" @click="remove(row)" aria-label="删除会话"><AppIcon name="trash" :size="18" /></button></div>
  </div><button v-if="hasMore" class="button load-more" :disabled="loading" @click="page++;load(false)">加载更多记录</button>
  <div v-if="editing" class="modal-overlay" @click.self="!saving && (editing=null)"><section class="modal panel" role="dialog" aria-modal="true" aria-labelledby="rename-title"><h2 id="rename-title">修改对话标题</h2><form @submit.prevent="saveTitle"><label>对话标题<input v-model="title" required maxlength="100" /></label><div class="form-actions"><button type="button" class="button" :disabled="saving" @click="editing=null">取消</button><button class="button primary" :disabled="saving">保存标题</button></div></form></section></div>
</template>
