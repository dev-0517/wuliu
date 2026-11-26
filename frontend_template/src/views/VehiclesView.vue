<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'
import { truckImage } from '../trucks'
import TrackMap from '../components/TrackMap.vue'

const items = ref([])
const branches = ref([])
const error = ref('')
const editing = ref(null)
const form = reactive({ plate: '', model: '', capacity_kg: 0, status: 'idle', branch_id: null })
const tracking = ref(null)
const trackLoading = ref(false)

async function showTrack(v) {
  trackLoading.value = true
  tracking.value = null
  try {
    tracking.value = await api.get(`/map/vehicle/${v.id}/tracking`)
  } catch (e) {
    error.value = e.message
  } finally {
    trackLoading.value = false
  }
}

const statusLabels = { idle: '空闲', transit: '运输中', maintenance: '维修中' }

async function load() {
  try {
    const [v, b] = await Promise.all([api.get('/vehicles'), api.get('/branches')])
    items.value = v
    branches.value = b
  } catch (e) {
    error.value = e.message
  }
}

function reset() {
  editing.value = null
  Object.assign(form, { plate: '', model: '', capacity_kg: 0, status: 'idle', branch_id: null })
}

function edit(v) {
  editing.value = v.id
  Object.assign(form, { plate: v.plate, model: v.model, capacity_kg: v.capacity_kg, status: v.status, branch_id: v.branch_id })
}

async function save() {
  error.value = ''
  try {
    const payload = { ...form, capacity_kg: Number(form.capacity_kg) || 0 }
    if (editing.value) await api.put(`/vehicles/${editing.value}`, payload)
    else await api.post('/vehicles', payload)
    reset()
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove(v) {
  if (!confirm(`确认删除车辆 ${v.plate}？`)) return
  try {
    await api.delete(`/vehicles/${v.id}`)
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
    <div class="panel">
      <div class="page-head">
        <h3>{{ editing ? '编辑车辆' : '新增车辆' }}</h3>
        <button v-if="editing" class="link" @click="reset">取消编辑</button>
      </div>
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
        <button class="primary" @click="save">{{ editing ? '保存' : '添加' }}</button>
      </div>
      <p v-if="error" class="err" style="margin: 10px 0 0">{{ error }}</p>
    </div>

    <table>
      <thead>
        <tr><th>图片</th><th>车牌</th><th>车型</th><th>载重</th><th>状态</th><th>归属网点</th><th style="width: 120px">操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="v in items" :key="v.id">
          <td><img :src="truckImage(v.model)" class="truck-img" :title="v.model || '车辆'" /></td>
          <td>
            <button v-if="v.status === 'transit'" class="link plate-link" @click="showTrack(v)">{{ v.plate }}</button>
            <template v-else>{{ v.plate }}</template>
          </td>
          <td>{{ v.model || '—' }}</td>
          <td>{{ v.capacity_kg }} kg</td>
          <td><span class="badge neutral">{{ statusLabels[v.status] || v.status }}</span></td>
          <td>{{ branchName(v.branch_id) }}</td>
          <td>
            <button class="link" @click="edit(v)">编辑</button>
            <button class="link" style="color: var(--danger); margin-left: 10px" @click="remove(v)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="!items.length" class="empty">暂无车辆</div>

    <div v-if="trackLoading" class="panel" style="margin-top: 14px">加载追踪中…</div>

    <div v-else-if="tracking" class="panel track-panel">
      <div class="page-head">
        <h3>🚚 {{ tracking.vehicle.plate }} 实时追踪</h3>
        <button class="link" @click="tracking = null">收起</button>
      </div>
      <div class="row" style="flex-wrap: wrap; gap: 24px; margin-bottom: 14px; font-size: 13px">
        <span><span class="muted">车型：</span>{{ tracking.vehicle.model || '—' }}</span>
        <span><span class="muted">状态：</span><span class="badge neutral">{{ statusLabels[tracking.vehicle.status] }}</span></span>
        <template v-if="tracking.order">
          <span><span class="muted">承运运单：</span><router-link :to="`/orders/${tracking.order.id}`" class="link">{{ tracking.order.order_no }}</router-link></span>
          <span><span class="muted">货物：</span>{{ tracking.order.goods }} · {{ tracking.order.weight_kg }} kg</span>
          <span><span class="muted">线路：</span>{{ tracking.location?.from_city }} → {{ tracking.location?.to_city }}</span>
          <span v-if="tracking.location?.supported"><span class="muted">运输进度：</span>{{ Math.round(tracking.location.progress * 100) }}%</span>
        </template>
        <span v-else class="muted">当前没有运输中的运单</span>
      </div>
      <TrackMap v-if="tracking.order" :order-id="tracking.order.id" />
    </div>
  </div>
</template>

<style scoped>
.truck-img { width: 64px; height: 46px; object-fit: cover; border-radius: 6px; display: block; }
.plate-link { font-weight: 600; }
.track-panel { margin-top: 14px; }
</style>
