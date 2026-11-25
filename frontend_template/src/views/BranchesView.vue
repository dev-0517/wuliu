<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'

const items = ref([])
const error = ref('')
const editing = ref(null)
const form = reactive({ code: '', name: '', city: '', address: '', phone: '' })

async function load() {
  try {
    items.value = await api.get('/branches')
  } catch (e) {
    error.value = e.message
  }
}

function reset() {
  editing.value = null
  Object.assign(form, { code: '', name: '', city: '', address: '', phone: '' })
}

function edit(b) {
  editing.value = b.id
  Object.assign(form, { code: b.code, name: b.name, city: b.city, address: b.address, phone: b.phone })
}

async function save() {
  error.value = ''
  if (!form.code || !form.name) {
    error.value = '编码与名称必填'
    return
  }
  try {
    if (editing.value) await api.put(`/branches/${editing.value}`, { ...form })
    else await api.post('/branches', { ...form })
    reset()
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove(b) {
  if (!confirm(`确认删除网点 ${b.name}？`)) return
  try {
    await api.delete(`/branches/${b.id}`)
    await load()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="panel">
      <div class="page-head">
        <h3>{{ editing ? '编辑网点' : '新增网点' }}</h3>
        <button v-if="editing" class="link" @click="reset">取消编辑</button>
      </div>
      <div class="row">
        <input v-model="form.code" placeholder="编码 如 HZ01" style="width: 130px" />
        <input v-model="form.name" placeholder="网点名称" style="width: 180px" />
        <input v-model="form.city" placeholder="城市" style="width: 110px" />
        <input v-model="form.address" placeholder="地址" class="grow" />
        <input v-model="form.phone" placeholder="电话" style="width: 140px" />
        <button class="primary" @click="save">{{ editing ? '保存' : '添加' }}</button>
      </div>
      <p v-if="error" class="err" style="margin: 10px 0 0">{{ error }}</p>
    </div>

    <table>
      <thead>
        <tr><th>编码</th><th>名称</th><th>城市</th><th>地址</th><th>电话</th><th style="width: 120px">操作</th></tr>
      </thead>
      <tbody>
        <tr v-for="b in items" :key="b.id">
          <td>{{ b.code }}</td>
          <td>{{ b.name }}</td>
          <td>{{ b.city }}</td>
          <td class="muted">{{ b.address || '—' }}</td>
          <td>{{ b.phone || '—' }}</td>
          <td>
            <button class="link" @click="edit(b)">编辑</button>
            <button class="link" style="color: var(--danger); margin-left: 10px" @click="remove(b)">删除</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="!items.length" class="empty">暂无网点</div>
  </div>
</template>
