<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'

const route = useRoute()
const router = useRouter()
const id = route.params.id

const detail = ref(null)
const error = ref('')
const editing = ref(false)
const form = reactive({ code: '', name: '', city: '', address: '', phone: '' })

const vehicleLabels = { idle: '空闲', transit: '运输中', maintenance: '维修中' }
const driverLabels = { available: '待命', driving: '出车中', rest: '休息' }
const orderLabels = { pending: '待揽收', picked: '已揽收', transit: '运输中', delivered: '已签收', exception: '异常' }

async function load() {
  try {
    detail.value = await api.get(`/branches/${id}/detail`)
    const b = detail.value.branch
    Object.assign(form, { code: b.code, name: b.name, city: b.city, address: b.address, phone: b.phone })
  } catch (e) {
    error.value = e.message
  }
}

async function save() {
  error.value = ''
  try {
    await api.put(`/branches/${id}`, { ...form })
    editing.value = false
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove() {
  if (!confirm(`确认删除网点 ${detail.value.branch.name}？`)) return
  try {
    await api.delete(`/branches/${id}`)
    router.push('/branches')
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div v-if="detail">
    <div class="page-head">
      <h3>网点详情 · {{ detail.branch.name }}</h3>
      <router-link to="/branches"><button>← 返回列表</button></router-link>
    </div>

    <div class="panel" v-if="!editing">
      <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 14px">
        <span class="avatar" style="background: var(--ok); width: 56px; height: 56px; font-size: 22px">{{ detail.branch.city?.[0] || detail.branch.name?.[0] || '网' }}</span>
        <div>
          <div class="card-title" style="font-size: 17px; margin-bottom: 4px"><span>{{ detail.branch.name }}</span><span class="badge neutral">{{ detail.branch.code }}</span></div>
          <div class="card-sub">{{ detail.branch.city }} · {{ detail.branch.address || '—' }}</div>
        </div>
      </div>
      <div class="card-row" style="margin-bottom: 6px"><span class="k">电话</span><span>{{ detail.branch.phone || '—' }}</span></div>
      <div class="card-row" style="margin-bottom: 6px"><span class="k">车辆</span><span>{{ detail.vehicles.length }} 辆</span></div>
      <div class="card-row" style="margin-bottom: 6px"><span class="k">司机</span><span>{{ detail.drivers.length }} 人</span></div>
      <div class="row" style="margin-top: 12px">
        <button class="primary" @click="editing = true">编辑</button>
        <button style="color: var(--danger)" @click="remove">删除</button>
      </div>
    </div>

    <div class="panel" v-else>
      <div class="row" style="margin-bottom: 10px">
        <input v-model="form.code" placeholder="编码" style="width: 130px" />
        <input v-model="form.name" placeholder="网点名称" style="width: 180px" />
        <input v-model="form.city" placeholder="城市" style="width: 110px" />
        <input v-model="form.phone" placeholder="电话" style="width: 140px" />
      </div>
      <div class="row" style="margin-bottom: 10px">
        <input v-model="form.address" placeholder="地址" class="grow" />
      </div>
      <div class="row">
        <button class="primary" @click="save">保存</button>
        <button @click="editing = false">取消</button>
      </div>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <div class="panel" v-if="detail.vehicles.length">
      <div class="page-head"><h3>网点车辆</h3></div>
      <div class="card-grid">
        <div v-for="v in detail.vehicles" :key="v.id" class="card-item" @click="$router.push(`/vehicles/${v.id}`)">
          <div class="card-title"><span>{{ v.plate }}</span><span class="badge neutral">{{ vehicleLabels[v.status] }}</span></div>
          <div class="card-row"><span class="k">车型</span><span>{{ v.model || '—' }}</span></div>
          <div class="card-foot"><span class="card-sub">查看详情 ›</span></div>
        </div>
      </div>
    </div>

    <div class="panel" v-if="detail.drivers.length">
      <div class="page-head"><h3>网点司机</h3></div>
      <div class="card-grid">
        <div v-for="d in detail.drivers" :key="d.id" class="card-item" @click="$router.push(`/drivers/${d.id}`)">
          <div style="display: flex; align-items: center; gap: 12px">
            <span class="avatar">{{ d.name?.[0] }}</span>
            <div class="card-title">{{ d.name }}</div>
            <span class="badge neutral" style="margin-left: auto">{{ driverLabels[d.status] }}</span>
          </div>
          <div class="card-row"><span class="k">电话</span><span>{{ d.phone || '—' }}</span></div>
          <div class="card-foot"><span class="card-sub">查看详情 ›</span></div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="page-head"><h3>相关运单</h3></div>
      <div class="card-grid" v-if="detail.orders.length">
        <div v-for="o in detail.orders" :key="o.id" class="card-item" @click="$router.push(`/orders/${o.id}`)">
          <div class="card-title">
            <span>{{ o.order_no }}</span>
            <span class="badge" :class="o.status">{{ orderLabels[o.status] }}</span>
          </div>
          <div class="card-row"><span class="k">货物</span><span>{{ o.goods }} · {{ o.weight_kg }} kg</span></div>
          <div class="card-foot"><span class="card-sub">{{ o.created_at }}</span><span class="card-sub">查看详情 ›</span></div>
        </div>
      </div>
      <div v-else class="empty">暂无相关运单</div>
    </div>
  </div>
  <div v-else-if="error" class="empty">{{ error }}</div>
  <div v-else class="empty">加载中…</div>
</template>
