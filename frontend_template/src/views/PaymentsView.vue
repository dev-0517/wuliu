<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'

const rows = ref([])
const toast = ref('')
const filter = ref('all')

const STATUS = {
  paid: { label: '待审核', cls: 's-paid' },
  approved: { label: '已批准', cls: 's-approved' },
  rejected: { label: '已驳回', cls: 's-rejected' },
}

async function load() {
  rows.value = await api.get('/payments')
}

async function act(r, action) {
  try {
    const data = await api.post(`/payments/${r.id}/${action}`, {})
    toast.value = data.message
    await load()
  } catch (e) {
    toast.value = e.message
  }
  setTimeout(() => toast.value = '', 2400)
}

onMounted(load)
</script>

<template>
  <div>
    <div class="filter-row">
      <select v-model="filter">
        <option value="all">全部记录</option>
        <option value="paid">待审核</option>
        <option value="approved">已批准</option>
        <option value="rejected">已驳回</option>
      </select>
    </div>

    <div class="card-grid">
      <div v-for="r in rows.filter(x => filter === 'all' || x.status === filter)" :key="r.id" class="card-item pay-card">
        <div class="pay-head">
          <b>{{ r.order_no }}</b>
          <span class="badge" :class="STATUS[r.status]?.cls">{{ STATUS[r.status]?.label }}</span>
        </div>
        <div>{{ r.goods }}</div>
        <div class="muted">用户：{{ r.username }} · {{ r.created_at }}</div>
        <div class="pay-foot">
          <span class="method">{{ r.method === 'wechat' ? '💚 微信支付' : '💙 支付宝' }}</span>
          <span class="amount">¥{{ r.amount }}</span>
        </div>
        <div v-if="r.status === 'paid'" class="btns">
          <button class="ok" @click="act(r, 'approve')">批准发货</button>
          <button class="no" @click="act(r, 'reject')">驳回</button>
        </div>
        <div v-else-if="r.reviewed_at" class="muted">处理时间：{{ r.reviewed_at }}</div>
      </div>
    </div>
    <div v-if="!rows.length" class="empty">暂无支付记录，用户在 APP 商城付款后会出现在这里</div>

    <div v-if="toast" class="toast-tip">{{ toast }}</div>
  </div>
</template>

<style scoped>
.filter-row { margin-bottom: 14px; }
.filter-row select { padding: 7px 12px; border: 1px solid #d1d5db; border-radius: 8px; }
.pay-card { min-width: 260px; }
.pay-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.badge { font-size: 12px; padding: 2px 10px; border-radius: 999px; }
.s-paid { background: #fef3c7; color: #b45309; }
.s-approved { background: #dcfce7; color: #15803d; }
.s-rejected { background: #fee2e2; color: #b91c1c; }
.pay-foot { display: flex; justify-content: space-between; margin: 8px 0; font-weight: 600; }
.amount { color: #dc2626; font-size: 17px; }
.btns { display: flex; gap: 8px; }
.btns button { flex: 1; padding: 7px 0; border-radius: 8px; font-size: 13px; }
.btns .ok { background: #16a34a; color: #fff; }
.btns .no { background: #f3f4f6; color: #6b7280; }
.toast-tip { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); background: #111827; color: #fff; padding: 10px 20px; border-radius: 10px; }
.empty { color: #9ca3af; text-align: center; padding: 40px 0; }
</style>
