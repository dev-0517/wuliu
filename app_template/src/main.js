import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Branches from './pages/Branches.vue'
import Home from './pages/Home.vue'
import Login from './pages/Login.vue'
import Mall from './pages/Mall.vue'
import Me from './pages/Me.vue'
import OrderDetail from './pages/OrderDetail.vue'
import './style.css'

const router = createRouter({
  history: createWebHashHistory('/app/'),
  routes: [
    { path: '/login', component: Login },
    { path: '/', component: Home },
    { path: '/order/:id', component: OrderDetail },
    { path: '/branches', component: Branches },
    { path: '/mall', component: Mall },
    { path: '/me', component: Me },
  ],
})

// 未登录跳登录页（login 页自身除外）
router.beforeEach((to) => {
  if (to.path !== '/login' && !localStorage.getItem('app_token')) {
    return '/login'
  }
})

createApp(App).use(router).mount('#app')
