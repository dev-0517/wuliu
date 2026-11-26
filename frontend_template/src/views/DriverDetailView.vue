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
const branches = ref([])
const form = reactive({ name: '', phone: '', license_no: '', status: 'available', branch_id: null })

const statusLabels = { available: '待命', driving: '出车中', rest: '休息' }
const orderLabels = { pending: '待揽收', picked: '已揽收', transit: '运输中', delivered: '已签收', exception: '异常' }

async function load() {
  try {
    detail.value = await api.get(`/drivers/${id}/detail`)
    const d = detail.value.driver
    Object.assign(form, { name: d.name, phone: d.phone, license_no: d.license_no, status: d.status, branch_id: d.branch_id })
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
    await api.put(`/drivers/${id}`, { ...form })
    editing.value = false
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove() {
  if (!confirm(`确认删除司机 ${detail.value.driver.name}？`)) return
  try {
    await api.delete(`/drivers/${id}`)
    router.push('/drivers')
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div v-if="detail">
    <div class="page-head">
      <h3>司机详情 · {{ detail.driver.name }}</h3>
      <router-link to="/drivers"><button>← 返回列表</button></router-link>
    </div>

    <div class="panel" v-if="!editing">
      <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 14px">
        <span class="avatar" style="width: 56px; height: 56px; font-size: 22px">{{ detail.driver.name?.[0] || '司' }}</span>
        <div>
          <div class="card-title" style="font-size: 17px; margin-bottom: 4px">
            <span>{{ detail.driver.name }}</span>
            <span class="badge" :class="detail.driver.status === 'driving' ? 'transit' : 'neutral'">{{ statusLabels[detail.driver.status] }}</span>
          </div>
          <div class="card-sub">{{ detail.driver.phone || '—' }}</div>
        </div>
      </div>
      <div class="card-row" style="margin-bottom: 6px"><span class="k">驾照号</span><span>{{ detail.driver.license_no || '—' }}</span></div>
      <div class="card-row" style="margin-bottom: 6px"><span class="k">归属网点</span><span>{{ detail.branch_name || '—' }}</span></div>
      <div class="row" style="margin-top: 12px">
        <button class="primary" @click="startEdit">编辑</button>
        <button style="color: var(--danger)" @click="remove">删除</button>
      </div>
    </div>

    <div class="panel" v-else>
      <div class="row" style="margin-bottom: 10px">
        <input v-model="form.name" placeholder="姓名" style="width: 120px" />
        <input v-model="form.phone" placeholder="电话" style="width: 150px" />
        <input v-model="form.license_no" placeholder="驾照号" style="width: 200px" />
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

    <p v-if="error" class="err">{{ error }}</p>

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
          <div class="card-foot"><span class="badge" :class="o.status">{{ orderLabels[o.status] }}</span><span class="card-sub">查看详情 ›</span></div>
        </div>
      </div>
      <div v-else class="empty">暂无承运运单</div>
    </div>
  </div>
  <div v-else-if="error" class="empty">{{ error }}</div>
  <div v-else class="empty">加载中…</div>
</template>
