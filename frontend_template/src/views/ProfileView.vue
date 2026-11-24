<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useUserStore } from '../stores/user'
import api from '../api'
import AppIcon from '../components/AppIcon.vue'
const user=useUserStore(), router=useRouter(), nickname=ref(''), error=ref(''), notice=ref(''), busy=ref(false)
onMounted(async()=>{try { await user.loadProfile();nickname.value=user.profile.nickname } catch(e) { error.value=e.message }})
async function save() { busy.value=true;error.value='';notice.value='';try { await api.patch('/profile',{nickname:nickname.value});await user.loadProfile();notice.value='昵称已保存' } catch(e) { error.value=e.message } finally { busy.value=false } }
async function logout() { busy.value=true;try { await user.logout();router.push('/login') } catch(e) { error.value=e.message } finally { busy.value=false } }
</script>
<template><div class="page-heading"><span class="eyebrow">PERSONAL SPACE</span><h1>个人中心</h1><p>管理你的账号与个人工作空间。</p></div><p v-if="error" class="error" role="alert">{{ error }}</p><p v-if="notice" class="success" role="status">{{ notice }}</p><template v-if="user.profile"><section class="panel profile-header"><span class="avatar large">{{ user.profile.nickname.slice(0,1) }}</span><div><h2>{{ user.profile.nickname }}</h2><p>{{ user.profile.username }}</p></div><span class="badge">个人账号</span></section><div class="profile-grid"><section class="panel"><h3>基本资料</h3><form @submit.prevent="save"><label>账号<input :value="user.profile.username" disabled /></label><label>昵称<input v-model="nickname" required maxlength="50" /></label><button class="button primary" :disabled="busy">保存修改</button></form></section><div><section class="panel"><h3>我的工作空间</h3><div class="profile-counts"><RouterLink to="/cases"><strong>{{ user.profile.case_count }}</strong><span>案件</span></RouterLink><RouterLink to="/records"><strong>{{ user.profile.conversation_count }}</strong><span>咨询会话</span></RouterLink></div></section><section class="panel profile-links"><RouterLink to="/agreement">服务协议与隐私说明<AppIcon name="arrow" :size="17" /></RouterLink><button :disabled="busy" @click="logout">退出登录<AppIcon name="logout" :size="17" /></button></section></div></div></template></template>
