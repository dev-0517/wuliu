import { createRouter, createWebHistory } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: () => import('../views/LoginView.vue') },
    { path: '/agreement', component: () => import('../views/AgreementView.vue') },
    { path: '/', component: AppLayout, children: [
      { path: '', redirect: '/cases' },
      { path: 'cases', component: () => import('../views/CasesView.vue'), meta: { title: '我的案件' } },
      { path: 'cases/new', component: () => import('../views/CaseFormView.vue'), meta: { title: '新建案件' } },
      { path: 'cases/:id/edit', component: () => import('../views/CaseFormView.vue'), meta: { title: '编辑案情' } },
      { path: 'cases/:id', component: () => import('../views/CaseDetailView.vue'), meta: { title: '案件工作台' } },
      { path: 'assistant', component: () => import('../views/AssistantView.vue'), meta: { title: 'AI 助手' } },
      { path: 'chat/:id', component: () => import('../views/ChatView.vue'), meta: { title: '与小诺对话' } },
      { path: 'records', component: () => import('../views/RecordsView.vue'), meta: { title: '聊天记录' } },
      { path: 'profile', component: () => import('../views/ProfileView.vue'), meta: { title: '个人中心' } },
    ] },
    { path: '/:pathMatch(.*)*', redirect: '/cases' },
  ],
  scrollBehavior: () => ({ top: 0 }),
})
router.beforeEach(to => {
  document.title = `${to.meta.title || '欢迎'} · 华诺 AI`
  if (!['/login', '/agreement'].includes(to.path) && !sessionStorage.getItem('huanuo_token')) return '/login'
})
export default router
