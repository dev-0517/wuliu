<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'

const items = ref([])
const branches = ref([])
const error = ref('')
const editing = ref(null)
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

function reset() {
  editing.value = null
  Object.assign(form, { name: '', phone: '', license_no: '', status: 'available', branch_id: null })
}

function edit(d) {
  editing.value = d.id
  Object.assign(form, { name: d.name, phone: d.phone, license_no: d.license_no, status: d.status, branch_id: d.branch_id })
}

async function save() {
  error.value = ''
  if (!form.name) {
    error.value = '姓名必填'
    return
  }
  try {
    if (editing.value) await api.put(`/drivers/${editing.value}`, { ...form })
    else await api.post('/drivers', { ...form })
    reset()
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove(d) {
  if (!confirm(`确认删除司机 ${d.name}？`)) return
  try {
    await api.delete(`/drivers/${d.id}`)
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
        <h3>{{ editing ? '编辑司机' : '新增司机' }}</h3>
        <button v-if="editing" class="link" @click="reset">取消编辑</button>
      </div>
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
        <button class="primary" @click="save">{{ editing ? '保存' : '添加' }}</button>
      </div>
      <p v-if="error" class="err" style="margin: 10px 0 0">{{ error }}</p>
    </div>

    <table>
      <thead>
        <tr><th>姓名</th><th>电话</th><th>驾照号</th><th>状态</th><th>归属网点</th><th style="width: 120px">操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="d in items" :key="d.id">
          <td>{{ d.name }}</td>
          <td>{{ d.phone || '—' }}</td>
          <td>{{ d.license_no || '—' }}</td>
          <td><span class="badge neutral">{{ statusLabels[d.status] || d.status }}</span></td>
          <td>{{ branchName(d.branch_id) }}</td>
          <td>
            <button class="link" @click="edit(d)">编辑</button>
            <button class="link" style="color: var(--danger); margin-left: 10px" @click="remove(d)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="!items.length" class="empty">暂无司机</div>
  </div>
</template>
