<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
const route = useRoute(), router = useRouter(), busy = ref(false), loading = ref(false), error = ref('')
const form = reactive({ title: '', category: '劳动纠纷', description: '', goal: '', stage: '咨询准备' })
const categories = ['劳动纠纷','租房纠纷','消费纠纷','合同纠纷','婚姻家事','其他']
onMounted(async () => { if(route.params.id) { loading.value = true; try { const data = await api.get(`/cases/${route.params.id}`); for(const key of Object.keys(form)) form[key] = data[key] } catch(e) { error.value=e.message } finally { loading.value=false } } })
async function submit() {
  if(busy.value) return
  busy.value=true; error.value=''
  try { const data = route.params.id ? await api.put(`/cases/${route.params.id}`,form) : await api.post('/cases',form); router.push(`/cases/${data.id}`) }
  catch(e) { error.value=e.message } finally { busy.value=false }
}
</script>
<template><RouterLink class="back-link" :to="route.params.id ? `/cases/${route.params.id}` : '/cases'"><AppIcon name="back" :size="17" />返回案件</RouterLink><div class="page-heading"><span class="eyebrow">CASE INFORMATION</span><h1>{{ route.params.id ? '编辑案情' : '记录一个新的案件' }}</h1><p>先写下你知道的事实，尚不确定的信息可以注明。</p></div><div class="form-layout"><form class="panel case-form" @submit.prevent="submit"><p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="loading">正在读取案情…</p><fieldset :disabled="loading || busy"><label>案件名称<input v-model="form.title" required maxlength="100" placeholder="例如：某公司拖欠工资争议" /></label><div class="form-row"><label>案件类型<select v-model="form.category"><option v-for="c in categories" :key="c">{{ c }}</option></select></label><label>当前阶段<select v-model="form.stage"><option v-for="s in ['咨询准备','协商中','仲裁中','一审','二审','已结束']" :key="s">{{ s }}</option></select></label></div><label>事情经过 <span class="muted">至少 10 字</span><textarea v-model="form.description" required minlength="10" maxlength="12000" rows="9" placeholder="事情发生在什么时候？涉及哪些人？发生了什么？哪些信息已经有材料支持？" /></label><label>你希望解决什么问题<textarea v-model="form.goal" maxlength="2000" rows="3" placeholder="例如：整理欠薪经过，了解需要准备哪些材料" /></label><div class="form-actions"><RouterLink class="button" to="/cases">取消</RouterLink><button class="button primary" :disabled="busy || loading">{{ busy ? '正在保存…' : '保存案件' }}<AppIcon name="arrow" :size="18" /></button></div></fieldset></form><aside class="panel writing-guide"><span class="mini-badge">填写小提示</span><h3>事实越清楚，<br>整理越有帮助。</h3><ol><li>按时间顺序描述经过</li><li>区分亲历事实与个人判断</li><li>说明已经掌握的材料</li><li>隐去身份证号等敏感信息</li></ol><p>修改案情后，旧的 AI 整理结果会清除，需要重新生成。历史咨询会保留。</p></aside></div></template>
