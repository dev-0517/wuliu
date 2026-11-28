<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const tabs = [
  { path: '/', ico: '📦', label: '快递' },
  { path: '/branches', ico: '🏪', label: '网点' },
  { path: '/mall', ico: '🛍️', label: '商城' },
  { path: '/me', ico: '👤', label: '我的' },
]
const showTab = computed(() => !['/login', '/order'].some(p => route.path.startsWith(p)))
</script>

<template>
  <router-view />
  <nav v-if="showTab" class="tabbar">
    <router-link v-for="t in tabs" :key="t.path" :to="t.path" :class="{ on: route.path === t.path }">
      <span class="ico">{{ t.ico }}</span>{{ t.label }}
    </router-link>
  </nav>
</template>
