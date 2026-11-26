<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'

const items = ref([])
const branches = ref([])
const error = ref('')
const form = reactive({ name: '', phone: '', license_no: '', status: 'available', branch_id: null })

const statusLabels = { available: '待命', driving: '出车中', rest: '休息' }

async function load() {
  try {
    const [d, b] = await Promise.all([api.get('/drivers'), api.get('/branches')])
    items.value = d
    branches.value = b
  } catch (e) {
    error.value = e.message
  }
}

async function save() {
  error.value = ''
  if (!form.name) {
    error.value = '姓名必填'
    return
  }
  try {
    await api.post('/drivers', { ...form })
    Object.assign(form, { name: '', phone: '', license_no: '', status: 'available', branch_id: null })
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
      <h3>司机管理</h3>
      <span class="muted" style="font-size: 13px">点击卡片进入司机详情</span>
    </div>

    <div class="panel">
      <div class="page-head"><h3>新增司机</h3></div>
      <div class="row">
        <input v-model="form.name" placeholder="姓名" style="width: 120px" />
        <input v-model="form.phone" placeholder="电话" style="width: 150px" />
        <input v-model="form.license_no" placeholder="驾照号" style="width: 200px" />
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
      <div v-for="d in items" :key="d.id" class="card-item" @click="$router.push(`/drivers/${d.id}`)">
        <div style="display: flex; align-items: center; gap: 12px">
          <span class="avatar">{{ d.name?.[0] || '司' }}</span>
          <div>
            <div class="card-title" style="margin-bottom: 2px">{{ d.name }}</div>
            <div class="card-sub">{{ d.phone || '—' }}</div>
          </div>
          <span class="badge" :class="d.status === 'driving' ? 'transit' : 'neutral'" style="margin-left: auto">{{ statusLabels[d.status] || d.status }}</span>
        </div>
        <div class="card-row"><span class="k">驾照号</span><span>{{ d.license_no || '—' }}</span></div>
        <div class="card-row"><span class="k">归属网点</span><span>{{ branchName(d.branch_id) }}</span></div>
        <div class="card-foot"><span class="card-sub">查看详情 ›</span></div>
      </div>
    </div>
    <div v-if="!items.length" class="empty">暂无司机</div>
  </div>
</template>
