<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const user = JSON.parse(localStorage.getItem('app_user') || '{}')
const playing = ref(-1)

const videos = [
  { title: '干线运输 · 全国公路网络', src: '/promo/highway.mp4', poster: '/promo/highway.jpg' },
  { title: '智慧仓储 · 安全高效分拣', src: '/promo/warehouse.mp4', poster: '/promo/warehouse.jpg' },
  { title: '数据驱动 · 运营实时洞察', src: '/promo/data.mp4', poster: '/promo/data.jpg' },
]

function play(i, e) {
  const v = e.target
  if (playing.value !== i) {
    document.querySelectorAll('video').forEach(x => { x.pause(); x.currentTime = 0 })
    playing.value = i
    v.play().catch(() => {})
  } else {
    v.pause()
    playing.value = -1
  }
}

function logout() {
  localStorage.removeItem('app_token')
  localStorage.removeItem('app_user')
  router.replace('/login')
}
</script>

<template>
  <div class="page">
    <div class="hero">
      <div class="avatar">{{ (user.username || '?')[0] }}</div>
      <h1>{{ user.username }}</h1>
      <p>智运到家 · 注册会员</p>
    </div>

    <div class="card row" @click="router.push('/')">
      <span>📦</span><b>我的快递</b><span class="arrow">›</span>
    </div>
    <div class="card row" @click="router.push('/branches')">
      <span>🏪</span><b>附近网点 / 寄件</b><span class="arrow">›</span>
    </div>
    <div class="card row" @click="router.push('/mall')">
      <span>🛍️</span><b>商城购物</b><span class="arrow">›</span>
    </div>

    <div class="sec-head"><b>品牌宣传视频</b><span class="muted">点击播放</span></div>
    <div v-for="(v, i) in videos" :key="v.title" class="card">
      <b style="font-size:14px">{{ v.title }}</b>
      <video style="width:100%;aspect-ratio:16/9;border-radius:10px;margin-top:8px;object-fit:cover;background:#0f172a"
             :src="v.src" :poster="v.poster" muted loop playsinline preload="metadata" @click="play(i, $event)"></video>
    </div>

    <button class="logout" @click="logout">退出登录</button>
  </div>
</template>

<style scoped>
.avatar {
  width: 54px; height: 54px; border-radius: 50%;
  background: #fff; color: #2563eb;
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 700; margin-bottom: 8px;
}
.hero { text-align: center; }
.row { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.row b { flex: 1; font-size: 15px; }
.row .arrow { color: #d1d5db; font-size: 18px; }
.sec-head { display: flex; justify-content: space-between; margin: 4px 2px 10px; }
.logout {
  width: 100%; height: 44px; border-radius: 22px;
  background: #fff; color: #dc2626; margin-top: 16px;
  box-shadow: 0 2px 10px rgba(31,41,55,.06);
}
</style>
