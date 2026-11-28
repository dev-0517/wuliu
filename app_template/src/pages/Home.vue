<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const user = JSON.parse(localStorage.getItem('app_user') || '{}')
const orders = ref([])
const loading = ref(true)
const videos = [
  { title: '干线运输', src: '/promo/highway.mp4', poster: '/promo/highway.jpg' },
  { title: '智慧仓储', src: '/promo/warehouse.mp4', poster: '/promo/warehouse.jpg' },
  { title: '数据驱动', src: '/promo/data.mp4', poster: '/promo/data.jpg' },
]
const videoIdx = ref(0)

const STATUS_ICON = { pending: '📥', picked: '📮', transit: '🚚', delivered: '✅', exception: '⚠️' }

async function load() {
  try {
    orders.value = await api.get('/mobile/my-orders')
  } catch (e) { /* 401 已由拦截器处理 */ }
  loading.value = false
}
onMounted(load)

function play(e) {
  const v = e.target
  if (v.paused) v.play().catch(() => {})
  else v.pause()
}
</script>

<template>
  <div class="page">
    <div class="hero">
      <h1>智运到家</h1>
      <p>{{ user.username }} · 快递动态实时掌握</p>
    </div>

    <!-- 功能入口 -->
    <div class="card" style="margin-top:-30px">
      <div class="entry-grid">
        <div class="entry" @click="router.push('/branches')"><div class="ico">📍</div><div class="txt">附近网点</div></div>
        <div class="entry" @click="router.push('/branches?send=1')"><div class="ico">📤</div><div class="txt">我要寄件</div></div>
        <div class="entry" @click="router.push('/mall')"><div class="ico">🛍️</div><div class="txt">商城购物</div></div>
        <div class="entry" @click="router.push('/me')"><div class="ico">🎬</div><div class="txt">品牌视频</div></div>
      </div>
    </div>

    <!-- 品牌宣传视频（点击播放） -->
    <div class="card">
      <div class="sec-head">
        <b>品牌宣传</b><span class="muted">点击播放 / 暂停</span>
      </div>
      <div class="v-tabs">
        <span v-for="(v, i) in videos" :key="v.title" :class="{ on: videoIdx === i }" @click="videoIdx = i">{{ v.title }}</span>
      </div>
      <video class="promo" :src="videos[videoIdx].src" :poster="videos[videoIdx].poster"
             muted loop playsinline preload="metadata" @click="play"></video>
    </div>

    <!-- 我的快递 -->
    <div class="sec-head"><b>我的快递</b><span class="muted">共 {{ orders.length }} 件</span></div>
    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="!orders.length" class="empty">暂无快递，去商城下一单试试吧 🛍️</div>
    <div v-for="o in orders" :key="o.id" class="card order-card" @click="router.push(`/order/${o.id}`)">
      <div class="status-icon">{{ STATUS_ICON[o.status] || '📦' }}</div>
      <div class="mid">
        <div class="no">{{ o.order_no }} · {{ o.role }}</div>
        <div class="goods">{{ o.goods }}</div>
        <div class="muted">{{ o.created_at }} · {{ o.weight_kg }}kg</div>
      </div>
      <span class="badge" :class="o.status">{{ o.status_label }}</span>
    </div>
  </div>
</template>

<style scoped>
.sec-head { display: flex; justify-content: space-between; align-items: center; margin: 4px 2px 10px; }
.sec-head b { font-size: 15px; }
.v-tabs { display: flex; gap: 14px; margin-bottom: 8px; }
.v-tabs span { font-size: 13px; color: #6b7280; padding: 3px 10px; border-radius: 999px; background: #f3f4f6; }
.v-tabs span.on { color: #2563eb; background: #eff6ff; font-weight: 600; }
.promo { width: 100%; aspect-ratio: 16/9; border-radius: 10px; object-fit: cover; display: block; background: #0f172a; }
</style>
