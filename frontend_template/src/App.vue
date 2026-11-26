<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const isPublic = computed(() => route.meta.public)
const user = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')
  } catch {
    return null
  }
})

const menus = [
  { name: 'dashboard', label: '运营总览', path: '/' },
  { name: 'orders', label: '运单管理', path: '/orders' },
  { name: 'vehicles', label: '车辆管理', path: '/vehicles' },
  { name: 'drivers', label: '司机管理', path: '/drivers' },
  { name: 'branches', label: '网点管理', path: '/branches' },
  { name: 'ai', label: 'AI 助手', path: '/ai' }
]

function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<template>
  <router-view v-if="isPublic" />

  <div v-else class="layout">
    <aside class="sidebar">
      <h1>物流管理系统</h1>
      <nav>
        <router-link
          v-for="m in menus"
          :key="m.name"
          :to="m.path"
          :class="{ active: route.name === m.name || (m.name === 'orders' && route.name === 'order-detail') }"
        >
          {{ m.label }}
        </router-link>
      </nav>
    </aside>

    <div class="main">
      <header class="topbar">
        <h2>{{ route.meta.title || '物流管理系统' }}</h2>
        <div class="who">
          <span>{{ user?.username }}（{{ user?.role === 'admin' ? '管理员' : '操作员' }}）</span>
          <button class="link" @click="logout">退出</button>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>
