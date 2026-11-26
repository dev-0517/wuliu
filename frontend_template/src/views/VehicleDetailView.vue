<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { truckImage } from '../trucks'
import TrackMap from '../components/TrackMap.vue'

const route = useRoute()
const router = useRouter()
const id = route.params.id

const detail = ref(null)
const track = ref(null)
const error = ref('')
const editing = ref(false)
const branches = ref([])
const form = reactive({ plate: '', model: '', capacity_kg: 0, status: 'idle', branch_id: null })

const statusLabels = { idle: '空闲', transit: '运输中', maintenance: '维修中' }

async function load() {
  try {
    detail.value = await api.get(`/vehicles/${id}/detail`)
    const v = detail.value.vehicle
    Object.assign(form, { plate: v.plate, model: v.model, capacity_kg: v.capacity_kg, status: v.status, branch_id: v.branch_id })
    if (v.status === 'transit') {
      try { track.value = await api.get(`/map/vehicle/${id}/tracking`) } catch { /* 静默 */ }
    }
  } catch (e) {
    error.value = e.message
  }
}

async function startEdit() {
  editing.value = true
  if (!branches.value.length) {
    try { branches.value = await api.get('/branches') } catch { /* 静默 */ }
  }
}

async function save() {
  error.value = ''
  try {
    await api.put(`/vehicles/${id}`, { ...form, capacity_kg: Number(form.capacity_kg) || 0 })
    editing.value = false
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove() {
  if (!confirm(`确认删除车辆 ${detail.value.vehicle.plate}？`)) return
  try {
    await api.delete(`/vehicles/${id}`)
    router.push('/vehicles')
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div v-if="detail">
    <div class="page-head">
      <h3>车辆详情 · {{ detail.vehicle.plate }}</h3>
      <router-link to="/vehicles"><button>← 返回列表</button></router-link>
    </div>

    <div class="panel" style="display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap">
      <img :src="truckImage(detail.vehicle.model)" style="width: 200px; height: 140px; object-fit: cover; border-radius: 8px" />
      <div style="flex: 1; min-width: 260px" v-if="!editing">
        <div class="card-title" style="font-size: 17px; margin-bottom: 10px">
          <span>{{ detail.vehicle.plate }}</span>
          <span class="badge" :class="detail.vehicle.status === 'transit' ? 'transit' : 'neutral'">{{ statusLabels[detail.vehicle.status] }}</span>
        </div>
        <div class="card-row" style="margin-bottom: 6px"><span class="k">车型</span><span>{{ detail.vehicle.model || '—' }}</span></div>
        <div class="card-row" style="margin-bottom: 6px"><span class="k">载重</span><span>{{ detail.vehicle.capacity_kg }} kg</span></div>
        <div class="card-row" style="margin-bottom: 6px"><span class="k">归属网点</span><span>{{ detail.branch_name || '—' }}</span></div>
        <div class="row" style="margin-top: 12px">
          <button class="primary" @click="startEdit">编辑</button>
          <button style="color: var(--danger)" @click="remove">删除</button>
        </div>
      </div>
      <div style="flex: 1; min-width: 260px" v-else>
        <div class="row" style="margin-bottom: 10px">
          <input v-model="form.plate" placeholder="车牌号" style="width: 140px" />
          <input v-model="form.model" placeholder="车型" style="width: 200px" />
          <input v-model="form.capacity_kg" type="number" placeholder="载重 kg" style="width: 120px" />
        </div>
        <div class="row" style="margin-bottom: 10px">
          <select v-model="form.status" style="width: 120px">
            <option v-for="(v, k) in statusLabels" :key="k" :value="k">{{ v }}</option>
          </select>
          <select v-model="form.branch_id" style="width: 160px">
            <option :value="null">未归属网点</option>
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>
        <div class="row">
          <button class="primary" @click="save">保存</button>
          <button @click="editing = false">取消</button>
        </div>
      </div>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <div v-if="track && track.order" class="panel">
      <div class="page-head"><h3>🚚 实时追踪 · {{ track.location?.from_city }} → {{ track.location?.to_city }}</h3></div>
      <TrackMap :order-id="track.order.id" />
    </div>
    <div v-else-if="track && !track.order" class="panel muted">当前没有运输中的运单</div>

    <div class="panel">
      <div class="page-head"><h3>承运运单</h3></div>
      <div class="card-grid" v-if="detail.orders.length">
        <div v-for="o in detail.orders" :key="o.id" class="card-item" @click="$router.push(`/orders/${o.id}`)">
          <div class="card-title">
            <span>{{ o.order_no }}</span>
            <span class="badge neutral">{{ o.goods }}</span>
          </div>
          <div class="card-row"><span class="k">重量</span><span>{{ o.weight_kg }} kg</span></div>
          <div class="card-row"><span class="k">时间</span><span class="card-sub">{{ o.created_at }}</span></div>
          <div class="card-foot"><span class="badge" :class="o.status">{{ { pending: '待揽收', picked: '已揽收', transit: '运输中', delivered: '已签收', exception: '异常' }[o.status] }}</span><span class="card-sub">查看详情 ›</span></div>
        </div>
      </div>
      <div v-else class="empty">暂无承运运单</div>
    </div>
  </div>
  <div v-else-if="error" class="empty">{{ error }}</div>
  <div v-else class="empty">加载中…</div>
</template>
