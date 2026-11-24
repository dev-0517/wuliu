<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
import AnalysisReport from '../components/AnalysisReport.vue'
const route = useRoute(), router = useRouter(), item = ref(null), materials = ref([])
const error = ref(''), notice = ref(''), busy = ref(false), analyzing = ref(false), starting = ref(false), tab = ref('overview'), editing = ref(null), showMaterial = ref(false)
const revisions=ref([]), revisionKey=ref('current'), historical=ref(null), versionBusy=ref(false), historyPage=ref(1), moreHistory=ref(false)
const pdfInput = ref(null), uploadingPdf = ref(false)
const displayedAnalysis=computed(()=>revisionKey.value==='current' ? item.value?.analysis : historical.value)
const form = reactive({ name: '', description: '', status: '待补充' })
async function load() {
  try {
    const [detail, materialRows, history]=await Promise.all([api.get(`/cases/${route.params.id}`),api.get(`/cases/${route.params.id}/materials`),api.get(`/cases/${route.params.id}/analysis/history`)])
    item.value=detail;materials.value=materialRows;revisions.value=history;revisionKey.value='current';historical.value=null;historyPage.value=1;moreHistory.value=history.length===20
  } catch(e) { error.value=e.message }
}
async function viewRevision() {
  if(revisionKey.value==='current') { historical.value=null;return }
  versionBusy.value=true;error.value=''
  try { const result=await api.get(`/cases/${item.value.id}/analysis/history/${revisionKey.value}`);historical.value=result.analysis }
  catch(e) { error.value=e.message;revisionKey.value='current';historical.value=null } finally { versionBusy.value=false }
}
async function loadMoreHistory() {
  versionBusy.value=true
  try { const rows=await api.get(`/cases/${item.value.id}/analysis/history`,{params:{page:historyPage.value+1}});revisions.value.push(...rows);historyPage.value++;moreHistory.value=rows.length===20 }
  catch(e) { error.value=e.message } finally { versionBusy.value=false }
}
function versionDate(value) { return new Date(value.endsWith('Z') ? value : value+'Z').toLocaleString('zh-CN',{hour12:false}) }
async function continueQuestion(question) { await startChat(`关于你提出的“${question}”，我的补充是：`) }
onMounted(load)
async function startChat(prompt='') { if(starting.value) return; starting.value=true; error.value=''; try { const c = await api.post('/conversations',{case_id:item.value.id}); router.push({path:`/chat/${c.id}`,query:typeof prompt==='string' && prompt ? {prompt} : {}}) } catch(e) { error.value=e.message } finally { starting.value=false } }
async function analyze() { if(analyzing.value) return; analyzing.value=true; error.value=''; notice.value=''; try { item.value.analysis=await api.post(`/cases/${item.value.id}/analysis`); await load(); notice.value='已生成深入分析并保存版本，原文引用已校验，事实仍需核实。' } catch(e) { error.value=e.message } finally { analyzing.value=false } }
function openMaterial(m) { editing.value=m?.id || null; Object.assign(form,{name:m?.name || '',description:m?.description || '',status:m?.status || '待补充'}); showMaterial.value=true }
async function saveMaterial() { busy.value=true; error.value=''; try { const url=`/cases/${item.value.id}/materials`; if(editing.value) await api.put(`${url}/${editing.value}`,form); else await api.post(url,form); showMaterial.value=false; await load() } catch(e) { error.value=e.message } finally { busy.value=false } }
async function deleteMaterial(m) { if(!window.confirm(`删除材料“${m.name}”？`)) return; try { await api.delete(`/cases/${item.value.id}/materials/${m.id}`); await load() } catch(e) { error.value=e.message } }
async function deleteCase() { if(!window.confirm('确定删除此案件及所有关联材料和咨询记录？删除后无法恢复。')) return; busy.value=true; try { await api.delete(`/cases/${item.value.id}`); router.push('/cases') } catch(e) { error.value=e.message } finally { busy.value=false } }
function pickPdf() { pdfInput.value?.click() }
async function uploadPdf(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.pdf')) { error.value = '仅支持 PDF 文件'; return }
  uploadingPdf.value = true; error.value = ''; notice.value = ''
  try {
    const body = new FormData()
    body.append('file', file)
    const result = await api.post(`/cases/${item.value.id}/materials/pdf`, body)
    await load()
    tab.value = 'materials'
    notice.value = `已从 PDF 导入 ${result.imported} 条文字材料。可前往「AI 案情梳理」生成分析。`
  } catch (e) { error.value = e.message }
  finally { uploadingPdf.value = false }
}
</script>
<template><RouterLink class="back-link" to="/cases"><AppIcon name="back" :size="17" />我的案件</RouterLink><p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" class="success" role="status">{{ notice }}</p><p v-if="!item && !error" class="empty-state">正在读取案件…</p><template v-if="item"><div class="detail-heading"><div><span class="eyebrow">CASE / {{ String(item.id).padStart(4,'0') }}</span><h1>{{ item.title }}</h1><div class="inline-meta"><span class="badge">{{ item.category }}</span><span>{{ item.stage }}</span><span>案情由用户录入</span></div></div><div class="button-group"><RouterLink class="button" :to="`/cases/${item.id}/edit`"><AppIcon name="edit" :size="17" />编辑案情</RouterLink><button class="button primary" :disabled="starting || analyzing" @click="startChat"><AppIcon name="spark" :size="18" />{{ starting ? '正在创建…' : '咨询这个案件' }}</button></div></div>
<div class="detail-stats"><div><AppIcon name="file" /><span>材料记录<strong>{{ materials.length }} 项</strong></span></div><div><AppIcon name="check" /><span>标记已有<strong>{{ materials.filter(m=>m.status==='已有').length }} 项</strong></span></div><div><AppIcon name="spark" /><span>AI 案情整理<strong>{{ item.analysis ? '已生成 · 待核实' : '尚未生成' }}</strong></span></div></div>
<div class="tabs"><button :class="{selected:tab==='overview'}" @click="tab='overview'">案情概览</button><button :class="{selected:tab==='analysis'}" @click="tab='analysis'">AI 案情梳理</button><button :class="{selected:tab==='materials'}" @click="tab='materials'">材料清单 <span class="count">{{ materials.length }}</span></button></div>
<template v-if="tab==='overview'"><div class="detail-columns"><section class="panel prose"><h3><AppIcon name="case" />事情经过</h3><p class="preserve">{{ item.description }}</p><h3>当前诉求</h3><p class="preserve">{{ item.goal || '尚未填写' }}</p></section><aside class="panel action-panel"><span class="empty-icon"><AppIcon name="spark" :size="28" /></span><h3>从案情，走向清晰</h3><p>让 AI 根据已录入信息，整理事实、时间线与待补充材料。</p><button class="button primary full" @click="tab='analysis'">查看案情梳理<AppIcon name="arrow" :size="17" /></button><p class="small">没有记录的信息不会自动变成事实。</p></aside></div></template>
<section v-if="tab==='analysis'" class="panel analysis-panel">
  <div class="section-heading"><div><h2>AI 案情梳理</h2><p>结合原文分析事实、争议、材料缺口与下一步</p></div><button class="button primary" :disabled="analyzing || busy || versionBusy" @click="analyze"><AppIcon name="spark" :size="18" />{{ analyzing ? '正在深入分析…' : item.analysis ? '重新整理' : '生成案情整理' }}</button></div>
  <div v-if="revisions.length" class="analysis-versions"><label>查看分析版本<select v-model="revisionKey" :disabled="versionBusy || analyzing" @change="viewRevision"><option value="current">当前结果{{ item.analysis ? '' : '（案情已更新，待重新生成）' }}</option><option v-for="version in revisions" :key="version.id" :value="String(version.id)">历史 #{{ version.id }} · {{ versionDate(version.created_at) }}</option></select></label><button v-if="moreHistory" class="text-button" :disabled="versionBusy || analyzing" @click="loadMoreHistory">更早的版本</button></div>
  <p v-if="revisionKey!=='current'" class="info">正在查看生成时的历史快照，当前案情或材料可能已经变化。</p>
  <p v-if="analyzing" class="info" role="status">正在根据当前记录生成分析，并核对来源编号、原文摘录与时间线日期。完成后会保存一个新版本。</p>
  <p v-if="versionBusy" class="empty-state" role="status">正在读取分析版本…</p>
  <div v-else-if="!displayedAnalysis" class="empty-state"><AppIcon name="file" :size="35" /><h3>{{ revisions.length ? '案情已更新，请重新分析' : '还没有整理结果' }}</h3><p>{{ revisions.length ? '之前的分析仍保留在上方历史版本中。' : '录入案情与材料后，生成有来源、可追问的深入分析。' }}</p></div>
  <AnalysisReport v-else :analysis="displayedAnalysis" :asking="starting || analyzing" @ask="continueQuestion" />
</section>
<section v-if="tab==='materials'" class="panel"><div class="section-heading"><div><h2>案件材料清单</h2><p>可手工记录，也可上传 PDF 提取文字（扫描件暂不支持 OCR）</p></div><div class="button-group"><input ref="pdfInput" type="file" accept="application/pdf,.pdf" hidden @change="uploadPdf" /><button class="button" :disabled="analyzing || uploadingPdf" @click="pickPdf"><AppIcon name="file" :size="18" />{{ uploadingPdf ? '正在导入 PDF…' : '上传 PDF' }}</button><button class="button primary" :disabled="analyzing || uploadingPdf" @click="openMaterial()"><AppIcon name="plus" :size="18" />记录材料</button></div></div><div v-if="!materials.length" class="empty-state"><AppIcon name="file" :size="32" /><h3>尚未记录材料</h3><p>可以记录已有材料，或上传 PDF 提取文字后用于 AI 案情梳理。</p></div><div v-for="m in materials" :key="m.id" class="material-row"><span class="case-type-icon"><AppIcon name="file" /></span><div class="material-text"><h3>{{ m.name }}</h3><p class="preserve">{{ m.description || '暂无说明' }}</p></div><span class="badge" :class="m.status==='已有' ? 'green' : ''">{{ m.status }}</span><button class="icon-button" :disabled="analyzing || uploadingPdf" @click="openMaterial(m)" aria-label="编辑材料"><AppIcon name="edit" :size="18" /></button><button class="icon-button danger" :disabled="analyzing || uploadingPdf" @click="deleteMaterial(m)" aria-label="删除材料"><AppIcon name="trash" :size="18" /></button></div></section>
<div class="danger-zone"><span>案件删除后，其材料与咨询记录一并删除。</span><button class="text-button danger" :disabled="busy || analyzing || starting" @click="deleteCase">删除案件</button></div>
<div v-if="showMaterial" class="modal-overlay" @click.self="showMaterial=false"><section class="modal panel" role="dialog" aria-modal="true" aria-labelledby="material-title"><h2 id="material-title">{{ editing ? '编辑材料记录' : '记录一项材料' }}</h2><form @submit.prevent="saveMaterial"><label>材料名称<input v-model="form.name" maxlength="100" required placeholder="例如：劳动合同、沟通记录" /></label><label>说明<textarea v-model="form.description" maxlength="3000" rows="4" placeholder="材料包含什么？来源是什么？不要填写敏感证件号码。" /></label><label>持有状态<select v-model="form.status"><option>待补充</option><option>已有</option></select></label><p v-if="error" class="error">{{ error }}</p><div class="form-actions"><button type="button" class="button" :disabled="busy" @click="showMaterial=false">取消</button><button class="button primary" :disabled="busy">{{ busy ? '保存中…' : '保存材料' }}</button></div></form></section></div></template></template>
