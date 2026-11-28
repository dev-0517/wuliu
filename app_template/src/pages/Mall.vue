<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const products = ref([])
const toast = ref('')
const buying = ref(0)

async function load() {
  products.value = await api.get('/mobile/products')
}
onMounted(load)

async function buy(p) {
  buying.value = p.id
  try {
    const data = await api.post(`/mobile/buy/${p.id}`, {})
    toast.value = data.message
    setTimeout(() => toast.value = '', 2200)
  } catch (e) {
    toast.value = e.message
    setTimeout(() => toast.value = '', 2200)
  } finally { buying.value = 0 }
}
</script>

<template>
  <div class="page">
    <div class="hero">
      <h1>智运商城</h1>
      <p>下单后自动生成快递运单，物流全程可查</p>
    </div>

    <div class="grid">
      <div v-for="p in products" :key="p.id" class="card prod">
        <div class="thumb" :style="{ background: p.color }">{{ p.emoji }}</div>
        <b class="name">{{ p.name }}</b>
        <div class="muted desc">{{ p.desc }}</div>
        <div class="foot">
          <span class="price">¥{{ p.price }}</span>
          <button class="buy" :disabled="buying === p.id" @click="buy(p)">
            {{ buying === p.id ? '下单中…' : '购买' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.prod { padding: 12px; margin-bottom: 0; }
.thumb {
  aspect-ratio: 1/1; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 46px; margin-bottom: 8px;
}
.name { font-size: 14px; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.desc { margin: 3px 0 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.foot { display: flex; justify-content: space-between; align-items: center; }
.price { color: #dc2626; font-weight: 700; font-size: 16px; }
.buy {
  background: #2563eb; color: #fff; border-radius: 14px;
  padding: 5px 16px; font-size: 13px;
}
.buy:disabled { opacity: .55; }
</style>
