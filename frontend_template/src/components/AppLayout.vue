<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter, RouterLink, RouterView } from 'vue-router'
import { useUserStore } from '../stores/user'
import AppIcon from './AppIcon.vue'
const route = useRoute(), router = useRouter(), user = useUserStore()
const error = ref('')
const links = [{ to: '/cases', label: '我的案件', icon: 'case' }, { to: '/assistant', label: 'AI 助手', icon: 'spark' }, { to: '/records', label: '聊天记录', icon: 'history' }, { to: '/profile', label: '个人中心', icon: 'user' }]
onMounted(async () => { try { await user.loadProfile() } catch (e) { error.value = e.message } })
async function logout() { try { await user.logout(); router.push('/login') } catch(e) { error.value = e.message } }
</script>
<template>
  <div class="app-layout">
    <aside class="sidebar">
      <RouterLink to="/cases" class="brand"><span class="brand-mark"><AppIcon name="spark" :size="25" /></span><span>华诺 <b>AI</b><small>让每一步，都更清晰</small></span></RouterLink>
      <div class="nav-label">工作空间</div>
      <nav><RouterLink v-for="link in links" :key="link.to" :to="link.to" :class="{ active: route.path.startsWith(link.to) || (link.to === '/assistant' && route.path.startsWith('/chat')) }"><AppIcon :name="link.icon" />{{ link.label }}<span class="nav-dot" /></RouterLink></nav>
      <div class="sidebar-bottom"><div class="privacy-note"><AppIcon name="shield" /><strong>你的案件，独立保存</strong><p>仅当前账号可访问自己的案件与咨询记录。</p></div><button class="user-chip" @click="router.push('/profile')"><span class="avatar">{{ user.profile?.nickname?.slice(0, 1) || '诺' }}</span><span>{{ user.profile?.nickname || '我的账号' }}<small>个人工作空间</small></span></button></div>
    </aside>
    <div class="main-shell"><header class="topbar"><span class="breadcrumb">工作空间 <span>/</span> <strong>{{ route.meta.title }}</strong></span><div class="topbar-actions"><span class="version-label">v0.2 · 内部试用</span><button class="icon-button" @click="logout" aria-label="退出登录" title="退出登录"><AppIcon name="logout" /></button></div></header>
      <main class="main-content"><p v-if="error" class="error" role="alert">{{ error }}</p><RouterView :key="route.path" /></main>
      <footer class="app-footer">华诺 AI · 辅助梳理事实，帮助准备下一步 <span>AI 内容需核实，重要事项请咨询执业律师</span></footer>
    </div>
    <nav class="mobile-nav"><RouterLink v-for="link in links" :key="link.to" :to="link.to"><AppIcon :name="link.icon" /><span>{{ link.label }}</span></RouterLink></nav>
  </div>
</template>
