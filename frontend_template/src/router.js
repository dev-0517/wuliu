import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('./views/LoginView.vue'), meta: { public: true } },
  { path: '/', name: 'dashboard', component: () => import('./views/DashboardView.vue'), meta: { title: '运营总览' } },
  { path: '/orders', name: 'orders', component: () => import('./views/OrdersView.vue'), meta: { title: '运单管理' } },
  { path: '/orders/new', name: 'order-new', component: () => import('./views/OrderFormView.vue'), meta: { title: '新建运单' } },
  { path: '/orders/:id', name: 'order-detail', component: () => import('./views/OrderDetailView.vue'), meta: { title: '运单详情' } },
  { path: '/vehicles', name: 'vehicles', component: () => import('./views/VehiclesView.vue'), meta: { title: '车辆管理' } },
  { path: '/vehicles/:id', name: 'vehicle-detail', component: () => import('./views/VehicleDetailView.vue'), meta: { title: '车辆详情' } },
  { path: '/drivers', name: 'drivers', component: () => import('./views/DriversView.vue'), meta: { title: '司机管理' } },
  { path: '/drivers/:id', name: 'driver-detail', component: () => import('./views/DriverDetailView.vue'), meta: { title: '司机详情' } },
  { path: '/branches', name: 'branches', component: () => import('./views/BranchesView.vue'), meta: { title: '网点管理' } },
  { path: '/branches/:id', name: 'branch-detail', component: () => import('./views/BranchDetailView.vue'), meta: { title: '网点详情' } },
  { path: '/ai', name: 'ai', component: () => import('./views/AiChatView.vue'), meta: { title: 'AI 助手' } }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) return { name: 'login' }
  if (to.name === 'login' && token) return { name: 'dashboard' }
  document.title = to.meta.title ? `${to.meta.title} · 物流管理系统` : '物流管理系统'
  return true
})

export default router
