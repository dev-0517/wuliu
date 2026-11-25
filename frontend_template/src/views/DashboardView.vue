<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'

const stats = ref(null)
const recent = ref([])
const error = ref('')

const labels = {
  pending: '待揽收',
  picked: '已揽收',
  transit: '运输中',
  delivered: '已签收',
  exception: '异常'
}

onMounted(async () => {
  try {
    stats.value = await api.get('/stats')
    const page = await api.get('/orders', { params: { page: 1, size: 6 } })
    recent.value = page.items
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <div>
    <p v-if="error" class="err">{{ error }}</p>

    <div class="grid" v-if="stats">
      <div class="stat">
        <div class="label">运单总数</div>
        <div class="value">{{ stats.total_orders }}</div>
      </div>
      <div class="stat">
        <div class="label">今日新建</div>
        <div class="value">{{ stats.today_new }}</div>
      </div>
      <div class="stat">
        <div class="label">运输中</div>
        <div class="value">{{ stats.by_status.transit || 0 }}</div>
      </div>
      <div class="stat">
        <div class="label">待揽收</div>
        <div class="value">{{ stats.by_status.pending || 0 }}</div>
      </div>
      <div class="stat">
        <div class="label">网点 / 车辆 / 司机</div>
        <div class="value" style="font-size: 20px">
          {{ stats.branches }} / {{ stats.vehicles }} / {{ stats.drivers }}
        </div>
      </div>
    </div>

    <div class="panel" style="margin-top: 16px">
      <div class="page-head">
        <h3>最新运单</h3>
        <router-link to="/orders" class="muted" style="font-size: 13px">查看全部 →</router-link>
      </div>
      <table v-if="recent.length">
        <thead>
          <tr>
            <th>运单号</th>
            <th>寄件人</th>
            <th>收件人</th>
            <th>货物</th>
            <th>状态</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="o in recent" :key="o.id">
            <td><router-link :to="`/orders/${o.id}`">{{ o.order_no }}</router-link></td>
            <td>{{ o.sender_name }}</td>
            <td>{{ o.receiver_name }}</td>
            <td>{{ o.goods }}</td>
            <td><span class="badge" :class="o.status">{{ labels[o.status] }}</span></td>
            <td class="muted">{{ o.created_at?.replace('T', ' ').slice(0, 16) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无运单</div>
    </div>
  </div>
</template>
