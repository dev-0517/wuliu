<script setup>
import { onMounted, ref, watch } from 'vue'
import api from '../api'

const labels = { pending: '待揽收', picked: '已揽收', transit: '运输中', delivered: '已签收', exception: '异常' }
const status = ref('')
const keyword = ref('')
const page = ref(1)
const size = 15
const total = ref(0)
const items = ref([])
const error = ref('')
const loading = ref(false)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.get('/orders', { params: { status: status.value, keyword: keyword.value, page: page.value, size } })
    items.value = data.items
    total.value = data.total
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

let timer = null
watch(keyword, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    page.value = 1
    load()
  }, 300)
})
watch(status, () => {
  page.value = 1
  load()
})
watch(page, load)

const pages = () => Math.max(1, Math.ceil(total.value / size))
onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <h3>运单列表</h3>
      <router-link to="/orders/new"><button class="primary">新建运单</button></router-link>
    </div>

    <div class="row" style="margin-bottom: 12px">
      <select v-model="status" style="width: 140px">
        <option value="">全部状态</option>
        <option v-for="(v, k) in labels" :key="k" :value="k">{{ v }}</option>
      </select>
      <input v-model="keyword" placeholder="搜索运单号 / 姓名 / 电话 / 货物" style="width: 300px" />
      <span class="muted">共 {{ total }} 条</span>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <div class="card-grid">
      <div v-for="o in items" :key="o.id" class="card-item" @click="$router.push(`/orders/${o.id}`)">
        <div class="card-title">
          <span>{{ o.order_no }}</span>
          <span class="badge" :class="o.status">{{ labels[o.status] }}</span>
        </div>
        <div class="card-row"><span class="k">寄件人</span><span>{{ o.sender_name }} <span class="card-sub">{{ o.sender_phone }}</span></span></div>
        <div class="card-row"><span class="k">收件人</span><span>{{ o.receiver_name }} <span class="card-sub">{{ o.receiver_phone }}</span></span></div>
        <div class="card-row"><span class="k">货物</span><span>{{ o.goods }} · {{ o.weight_kg }} kg</span></div>
        <div class="card-foot">
          <span class="card-sub">{{ o.created_at?.replace('T', ' ').slice(0, 16) }}</span>
          <span class="card-sub">查看详情 ›</span>
        </div>
      </div>
    </div>
    <div v-if="!items.length && !loading" class="empty">没有符合条件的运单</div>

    <div class="row" style="margin-top: 12px; justify-content: flex-end">
      <button :disabled="page <= 1" @click="page--">上一页</button>
      <span class="muted">{{ page }} / {{ pages() }}</span>
      <button :disabled="page >= pages()" @click="page++">下一页</button>
    </div>
  </div>
</template>
