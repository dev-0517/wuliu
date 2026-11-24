<script setup>
import { ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useUserStore } from '../stores/user'
import AppIcon from '../components/AppIcon.vue'
const mode = ref('login'), busy = ref(false), error = ref('')
const form = ref({ username: '', password: '', nickname: '', agreed: false })
const user = useUserStore(), router = useRouter()
async function submit() {
  if (busy.value) return
  error.value = ''; busy.value = true
  try { await user.authenticate(mode.value, form.value); await router.push('/cases') }
  catch(e) { error.value = e.message } finally { busy.value = false }
}
</script>
<template><div class="login-page"><section class="login-story"><div class="brand"><span class="brand-mark"><AppIcon name="spark" :size="25" /></span>华诺 AI</div><span class="eyebrow">YOUR CASE, MADE CLEAR</span><h1>把复杂的案情，<br>整理成清晰的下一步。</h1><p>从事实梳理到材料准备，让 AI 成为你的案件辅助助手。</p><div class="story-card"><span class="mini-badge"><AppIcon name="check" :size="15" /> 有条理地准备</span><h3>每一份材料，都有迹可循</h3><div class="story-line"><span />梳理事情经过</div><div class="story-line"><span />记录已有材料</div><div class="story-line"><span />发现待补充信息</div></div><small>辅助整理，不代替专业法律意见</small></section>
<section class="login-form-panel"><div class="auth-box"><span class="eyebrow">WELCOME TO HUANUO</span><h2>{{ mode === 'login' ? '欢迎回来' : '创建你的工作空间' }}</h2><p class="muted">{{ mode === 'login' ? '登录后，继续梳理你的案件。' : '从记录第一件事开始。' }}</p><div class="segmented"><button :class="{selected: mode === 'login'}" @click="mode='login'; error=''">账号登录</button><button :class="{selected: mode === 'register'}" @click="mode='register'; error=''">注册账号</button></div>
<form @submit.prevent="submit"><label>账号<input v-model="form.username" required minlength="3" maxlength="50" autocomplete="username" placeholder="手机号、邮箱或英文账号" pattern="[a-zA-Z0-9_@.+-]+" /></label><label v-if="mode === 'register'">昵称<input v-model="form.nickname" required maxlength="50" autocomplete="nickname" placeholder="希望我们如何称呼你" /></label><label>密码<input v-model="form.password" type="password" required minlength="8" maxlength="128" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" placeholder="至少 8 位密码" /></label><label v-if="mode === 'register'" class="check-label"><input v-model="form.agreed" type="checkbox" required /><span>我已阅读并同意 <RouterLink to="/agreement" target="_blank">服务协议、隐私说明与 AI 使用说明</RouterLink></span></label><p v-if="error" class="error" role="alert">{{ error }}</p><button class="button primary full" :disabled="busy">{{ busy ? '正在处理…' : mode === 'login' ? '登录工作空间' : '注册并开始使用' }}<AppIcon name="arrow" /></button></form><div class="auth-foot"><AppIcon name="shield" :size="16" />案件数据按账号隔离保存</div></div></section></div></template>
