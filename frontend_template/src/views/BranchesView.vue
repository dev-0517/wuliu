<script setup>
import { onMounted, reactive, ref } from 'vue'
import api from '../api'

const items = ref([])
const error = ref('')
const form = reactive({ code: '', name: '', city: '', address: '', phone: '' })

async function load() {
  try {
    items.value = await api.get('/branches')
  } catch (e) {
    error.value = e.message
  }
}

async function save() {
  error.value = ''
  if (!form.code || !form.name) {
    error.value = '编码与名称必填'
    return
  }
  try {
    await api.post('/branches', { ...form })
    Object.assign(form, { code: '', name: '', city: '', address: '', phone: '' })
    await load()
  } catch (e) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <h3>网点管理</h3>
      <span class="muted" style="font-size: 13px">点击卡片进入网点详情</span>
    </div>

    <div class="panel">
      <div class="page-head"><h3>新增网点</h3></div>
      <div class="row">
        <input v-model="form.code" placeholder="编码 如 HZ01" style="width: 130px" />
        <input v-model="form.name" placeholder="网点名称" style="width: 180px" />
        <input v-model="form.city" placeholder="城市" style="width: 110px" />
        <input v-model="form.address" placeholder="地址" class="grow" />
        <input v-model="form.phone" placeholder="电话" style="width: 140px" />
        <button class="primary" @click="save">添加</button>
      </div>
      <p v-if="error" class="err" style="margin: 10px 0 0">{{ error }}</p>
    </div>

    <div class="card-grid">
      <div v-for="b in items" :key="b.id" class="card-item" @click="$router.push(`/branches/${b.id}`)">
        <div style="display: flex; align-items: center; gap: 12px">
          <span class="avatar" style="background: var(--ok)">{{ b.city?.[0] || b.name?.[0] || '网' }}</span>
          <div>
            <div class="card-title" style="margin-bottom: 2px">{{ b.name }}</div>
            <div class="card-sub">{{ b.code }}</div>
          </div>
        </div>
        <div class="card-row"><span class="k">城市</span><span>{{ b.city || '—' }}</span></div>
        <div class="card-row"><span class="k">地址</span><span>{{ b.address || '—' }}</span></div>
        <div class="card-row"><span class="k">电话</span><span>{{ b.phone || '—' }}</span></div>
        <div class="card-foot"><span class="card-sub">查看详情 ›</span></div>
      </div>
    </div>
    <div v-if="!items.length" class="empty">暂无网点</div>
  </div>
</template>
