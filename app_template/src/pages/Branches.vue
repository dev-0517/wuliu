<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()
const list = ref([])
const loading = ref(false)
const located = ref(false)
const toast = ref('')

const CITIES = { '杭州': [120.15, 30.28], '上海': [121.47, 31.23], '南京': [118.78, 32.06] }
const pos = ref(CITIES['杭州'])
const city = ref('杭州')

async function locate() {
  loading.value = true
  // 优先浏览器定位（需 https 权限，失败则用所选城市中心）
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      (p) => {
        pos.value = [p.coords.longitude, p.coords.latitude]
        located.value = true
        load()
      },
      () => { toastMsg('定位失败，已使用 ' + city.value + ' 市中心'); load() },
      { timeout: 5000 }
    )
  } else {
    load()
  }
}

async function pickCity(name) {
  city.value = name
  pos.value = CITIES[name]
  await load()
}

async function load() {
  loading.value = true
  try {
    list.value = await api.get(`/mobile/nearby?lat=${pos.value[1]}&lon=${pos.value[0]}`)
  } finally { loading.value = false }
}
onMounted(() => {
  locate()
  if (route.query.send) showSend.value = true
})

// ---------- 寄快递 ----------
const showSend = ref(false)
const form = ref({ receiver_name: '', receiver_phone: '', receiver_address: '', goods: '', weight_kg: 1 })
const sending = ref(false)

async function submitSend() {
  sending.value = true
  try {
    const data = await api.post('/mobile/send', form.value)
    toastMsg(data.message)
    showSend.value = false
    form.value = { receiver_name: '', receiver_phone: '', receiver_address: '', goods: '', weight_kg: 1 }
  } catch (e) { toastMsg(e.message) } finally { sending.value = false }
}

function toastMsg(msg) {
  toast.value = msg
  setTimeout(() => toast.value = '', 2200)
}
</script>

<template>
  <div class="page">
    <div class="hero">
      <h1>附近网点</h1>
      <p>就近取件 / 寄快递，步行几分钟就到</p>
      <div class="city-row">
        <span v-for="(c, name) in CITIES" :key="name" :class="{ on: city === name }" @click="pickCity(name)">{{ name }}</span>
        <button class="reloc" @click="locate">📍 重新定位</button>
      </div>
    </div>

    <button class="primary" style="margin-bottom:12px" @click="showSend = true">📤 我要寄件</button>

    <div v-if="loading" class="empty">定位中…</div>
    <div v-for="b in list" :key="b.id" class="card">
      <div class="b-head">
        <b>{{ b.name }}</b>
        <span class="dist">{{ b.distance_km }} km</span>
      </div>
      <div class="muted">{{ b.city }} · {{ b.address }}</div>
      <div class="muted">☎ {{ b.phone || '—' }} · 编码 {{ b.code }}</div>
    </div>

    <!-- 寄件表单 -->
    <div v-if="showSend" class="sheet-mask" @click.self="showSend = false">
      <div class="sheet">
        <h3>寄快递</h3>
        <div class="row"><label>收件人姓名</label><input v-model="form.receiver_name" placeholder="收件人姓名" /></div>
        <div class="row"><label>收件人电话</label><input v-model="form.receiver_phone" placeholder="收件人电话" maxlength="11" inputmode="numeric" /></div>
        <div class="row"><label>收件地址</label><input v-model="form.receiver_address" placeholder="省市区 详细地址" /></div>
        <div class="row"><label>物品名称</label><input v-model="form.goods" placeholder="如：衣物 / 文件 / 数码产品" /></div>
        <div class="row"><label>重量 (kg)</label><input v-model="form.weight_kg" type="number" step="0.1" min="0.1" /></div>
        <button class="primary" :disabled="sending" @click="submitSend">{{ sending ? '提交中…' : '确认下单' }}</button>
        <button class="ghost" @click="showSend = false">取消</button>
      </div>
    </div>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<style scoped>
.city-row { display: flex; gap: 8px; margin-top: 12px; align-items: center; flex-wrap: wrap; }
.city-row span { padding: 4px 14px; border-radius: 999px; background: rgba(255,255,255,.2); font-size: 13px; }
.city-row span.on { background: #fff; color: #2563eb; font-weight: 600; }
.reloc { margin-left: auto; background: rgba(255,255,255,.2); color: #fff; border-radius: 999px; padding: 4px 12px; font-size: 12px; }
.b-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.dist { color: #2563eb; font-size: 13px; font-weight: 600; }
.ghost { width: 100%; height: 40px; border-radius: 20px; background: #f3f4f6; margin-top: 10px; }
</style>
