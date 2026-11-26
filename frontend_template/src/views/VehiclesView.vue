<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'
import { truckImage } from '../trucks'

const items = ref([])
const branches = ref([])
const error = ref('')
const form = reactive({ plate: '', model: '', capacity_kg: 0, status: 'idle', branch_id: null })
const etas = ref({})   // vehicle_id -> {from_city, to_city, eta_time, remain_km, progress}

const statusLabels = { idle: '空闲', transit: '运输中', maintenance: '维修中' }

async function loadEtas() {
  try {
    const list = await api.get('/map/vehicles/etas')
    const m = {}
    for (const e of list) m[e.vehicle_id] = e
    etas.value = m
  } catch { /* 静默 */ }
}

async function load() {
  try {
    const [v, b] = await Promise.all([api.get('/vehicles'), api.get('/branches')])
    items.value = v
    branches.value = b
    await loadEtas()
  } catch (e) {
    error.value = e.message
  }
}

function reset() {
  Object.assign(form, { plate: '', model: '', capacity_kg: 0, status: 'idle', branch_id: null })
}

async function save() {
  error.value = ''
  try {
    const payload = { ...form, capacity_kg: Number(form.capacity_kg) || 0 }
    await api.post('/vehicles', payload)
    reset()
    await load()
  } catch (e) {
    error.value = e.message
  }
}

const branchName = (id) => branches.value.find((b) => b.id === id)?.name || '—'
onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <h3>车辆管理</h3>
      <span class="muted" style="font-size: 13px">点击卡片进入车辆详情</span>
    </div>

    <div class="panel">
      <div class="page-head"><h3>新增车辆</h3></div>
      <div class="row">
        <input v-model="form.plate" placeholder="车牌号" style="width: 140px" />
        <input v-model="form.model" placeholder="车型" style="width: 200px" />
        <input v-model="form.capacity_kg" type="number" placeholder="载重 kg" style="width: 120px" />
        <select v-model="form.status" style="width: 120px">
          <option v-for="(v, k) in statusLabels" :key="k" :value="k">{{ v }}</option>
        </select>
        <select v-model="form.branch_id" style="width: 160px">
          <option :value="null">未归属网点</option>
          <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
        </select>
        <button class="primary" @click="save">添加</button>
      </div>
      <p v-if="error" class="err" style="margin: 10px 0 0">{{ error }}</p>
    </div>

    <div class="card-grid">
      <div v-for="v in items" :key="v.id" class="card-item" @click="$router.push(`/vehicles/${v.id}`)">
        <img :src="truckImage(v.model)" class="card-img" :title="v.model || '车辆'" />
        <div class="card-title">
          <span>{{ v.plate }}</span>
          <span class="badge" :class="v.status === 'transit' ? 'transit' : 'neutral'">{{ statusLabels[v.status] || v.status }}</span>
        </div>
        <div class="card-row"><span class="k">车型</span><span>{{ v.model || '—' }}</span></div>
        <div class="card-row"><span class="k">载重</span><span>{{ v.capacity_kg }} kg</span></div>
        <div class="card-row"><span class="k">归属网点</span><span>{{ branchName(v.branch_id) }}</span></div>
        <div class="card-foot" v-if="etas[v.id]">
          <span><b style="color: var(--primary)">{{ etas[v.id].eta_time }}</b> 到{{ etas[v.id].to_city }}</span>
          <span class="card-sub">余 {{ etas[v.id].remain_km }}km ›</span>
        </div>
        <div class="card-foot" v-else>
          <span class="card-sub">查看详情 ›</span>
        </div>
      </div>
    </div>
    <div v-if="!items.length" class="empty">暂无车辆</div>
  </div>
</template>
