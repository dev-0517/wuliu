<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const order = ref(null)
const tracks = ref([])
const error = ref('')

const STEPS = [
  { key: 'pending', label: '已下单' },
  { key: 'picked', label: '已揽收' },
  { key: 'transit', label: '运输中' },
  { key: 'delivered', label: '已签收' },
]
const stepIdx = computed(() => {
  const s = order.value?.status
  if (s === 'exception') return 1
  return Math.max(0, STEPS.findIndex(x => x.key === s))
})

onMounted(async () => {
  try {
    order.value = await api.get(`/mobile/my-orders/${route.params.id}`)
    tracks.value = await api.get(`/mobile/my-orders/${route.params.id}/tracks`)
  } catch (e) { error.value = e.message }
})
</script>

<template>
  <div class="page" style="padding-top:0">
    <div class="hero" @click="$router.back()">← 返回</div>

    <div v-if="error" class="card">{{ error }}</div>
    <template v-else-if="order">
      <!-- 物流进度条 -->
      <div class="card">
        <div class="big-status">
          {{ { pending: '待揽收', picked: '已揽收', transit: '运输中', delivered: '已签收', exception: '异常' }[order.status] }}
        </div>
        <div class="steps">
          <div v-for="(s, i) in STEPS" :key="s.key" class="step" :class="{ done: i <= stepIdx, cur: i === stepIdx }">
            <span class="dot"></span><span class="lb">{{ s.label }}</span>
          </div>
        </div>
        <div class="meta">
          <div>运单号：{{ order.order_no }}</div>
          <div>货物：{{ order.goods }}（{{ order.weight_kg }}kg）</div>
          <div>寄件：{{ order.sender_address }}</div>
          <div>收件：{{ order.receiver_address }}</div>
        </div>
      </div>

      <!-- 轨迹时间线 -->
      <div class="card">
        <b>物流轨迹</b>
        <div class="tl">
          <div v-for="t in [...tracks].reverse()" :key="t.id" class="tl-item">
            <span class="tl-dot"></span>
            <div>
              <div class="tl-note">{{ t.note || t.location }}</div>
              <div class="muted">{{ t.created_at?.replace('T', ' ')?.slice(0, 16) }} · {{ t.location }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.hero { cursor: pointer; }
.big-status { font-size: 20px; font-weight: 700; margin-bottom: 12px; }
.steps { display: flex; justify-content: space-between; margin-bottom: 12px; }
.step { text-align: center; flex: 1; position: relative; }
.step .dot {
  display: block; width: 12px; height: 12px; border-radius: 50%;
  background: #e5e7eb; margin: 0 auto 4px;
}
.step.done .dot { background: #2563eb; }
.step.cur .dot { box-shadow: 0 0 0 4px rgba(37,99,235,.2); }
.step .lb { font-size: 11px; color: #9ca3af; }
.step.done .lb { color: #2563eb; }
.meta { font-size: 13px; color: #4b5563; line-height: 1.9; }
.tl { margin-top: 10px; }
.tl-item { position: relative; padding: 0 0 16px 18px; border-left: 2px solid #e5e7eb; }
.tl-item:last-child { border-left-color: transparent; padding-bottom: 0; }
.tl-dot {
  position: absolute; left: -6px; top: 3px;
  width: 10px; height: 10px; border-radius: 50%; background: #2563eb;
}
.tl-note { font-size: 13px; margin-bottom: 2px; }
</style>
