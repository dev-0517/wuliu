<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const order = ref(null)
const branches = ref([])
const error = ref('')
const saving = ref(false)

const labels = { pending: '待揽收', picked: '已揽收', transit: '运输中', delivered: '已签收', exception: '异常' }
const action = reactive({ status: '', location: '', note: '' })

const branchName = computed(() => {
  const map = Object.fromEntries(branches.value.map((b) => [b.id, b.name]))
  return (id) => (id ? map[id] || `#${id}` : '—')
})

async function load() {
  try {
    const [o, b] = await Promise.all([api.get(`/orders/${route.params.id}`), api.get('/branches')])
    order.value = o
    branches.value = b
    action.status = o.status === 'pending' ? 'picked' : o.status === 'picked' ? 'transit' : o.status === 'transit' ? 'delivered' : o.status
  } catch (e) {
    error.value = e.message
  }
}

async function changeStatus() {
  saving.value = true
  error.value = ''
  try {
    order.value = await api.post(`/orders/${order.value.id}/status`, { ...action })
    action.location = ''
    action.note = ''
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="page-head">
      <h3>运单详情</h3>
      <router-link to="/orders" class="muted" style="font-size: 13px">返回列表</router-link>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <template v-if="order">
      <div class="panel">
        <div class="row" style="justify-content: space-between">
          <div>
            <div style="font-size: 18px; font-weight: 600">{{ order.order_no }}</div>
            <div class="muted" style="margin-top: 4px">
              创建于 {{ order.created_at?.replace('T', ' ').slice(0, 19) }}
            </div>
          </div>
          <span class="badge" :class="order.status">{{ labels[order.status] }}</span>
        </div>

        <div class="form-grid" style="margin-top: 18px">
          <div>
            <div class="muted">寄件人</div>
            <div>{{ order.sender_name }} {{ order.sender_phone }}</div>
            <div class="muted">{{ order.sender_address }}</div>
          </div>
          <div>
            <div class="muted">收件人</div>
            <div>{{ order.receiver_name }} {{ order.receiver_phone }}</div>
            <div class="muted">{{ order.receiver_address }}</div>
          </div>
          <div>
            <div class="muted">起始网点 → 目的网点</div>
            <div>{{ branchName(order.origin_branch_id) }} → {{ branchName(order.dest_branch_id) }}</div>
          </div>
          <div>
            <div class="muted">货物 / 重量</div>
            <div>{{ order.goods || '—' }} · {{ order.weight_kg }} kg</div>
          </div>
          <div class="full">
            <div class="muted">备注</div>
            <div>{{ order.remark || '—' }}</div>
          </div>
        </div>
      </div>

      <div class="panel">
        <h3 style="margin: 0 0 12px; font-size: 14px">更新状态</h3>
        <div class="row">
          <select v-model="action.status" style="width: 140px">
            <option v-for="(v, k) in labels" :key="k" :value="k">{{ v }}</option>
          </select>
          <input v-model="action.location" placeholder="当前位置，如：嘉兴分拨中心" style="width: 240px" />
          <input v-model="action.note" placeholder="备注（可选）" class="grow" />
          <button class="primary" :disabled="saving" @click="changeStatus">{{ saving ? '提交中…' : '提交' }}</button>
        </div>
      </div>

      <div class="panel">
        <h3 style="margin: 0 0 14px; font-size: 14px">物流轨迹</h3>
        <ul class="timeline">
          <li v-for="t in [...order.tracks].reverse()" :key="t.id">
            <div>
              <span class="badge" :class="t.status">{{ labels[t.status] }}</span>
              <span style="margin-left: 8px">{{ t.location }}</span>
            </div>
            <div class="muted" style="margin-top: 4px">{{ t.note || '—' }}</div>
            <div class="t">{{ t.created_at?.replace('T', ' ').slice(0, 19) }}</div>
          </li>
        </ul>
        <div v-if="!order.tracks.length" class="empty">暂无轨迹</div>
      </div>
    </template>
  </div>
</template>
