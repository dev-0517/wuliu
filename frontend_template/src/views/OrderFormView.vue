<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const branches = ref([])
const drivers = ref([])
const vehicles = ref([])
const error = ref('')
const saving = ref(false)

const form = reactive({
  sender_name: '',
  sender_phone: '',
  sender_address: '',
  receiver_name: '',
  receiver_phone: '',
  receiver_address: '',
  origin_branch_id: null,
  dest_branch_id: null,
  driver_id: null,
  vehicle_id: null,
  goods: '',
  weight_kg: 0,
  remark: ''
})

onMounted(async () => {
  try {
    const [b, d, v] = await Promise.all([api.get('/branches'), api.get('/drivers'), api.get('/vehicles')])
    branches.value = b
    drivers.value = d
    vehicles.value = v
    if (b.length) {
      form.origin_branch_id = b[0].id
      form.dest_branch_id = b[Math.min(1, b.length - 1)].id
    }
  } catch (e) {
    error.value = e.message
  }
})

async function submit() {
  if (!form.sender_name || !form.receiver_name) {
    error.value = '寄件人与收件人姓名必填'
    return
  }
  saving.value = true
  error.value = ''
  try {
    const created = await api.post('/orders', { ...form, weight_kg: Number(form.weight_kg) || 0 })
    router.push(`/orders/${created.id}`)
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="panel">
    <div class="page-head">
      <h3>新建运单</h3>
      <router-link to="/orders" class="muted" style="font-size: 13px">返回列表</router-link>
    </div>

    <form @submit.prevent="submit">
      <div class="form-grid">
        <div>
          <label class="muted">寄件人 *</label>
          <input v-model="form.sender_name" placeholder="寄件人姓名" />
        </div>
        <div>
          <label class="muted">寄件人电话</label>
          <input v-model="form.sender_phone" placeholder="手机号" />
        </div>
        <div class="full">
          <label class="muted">寄件地址</label>
          <input v-model="form.sender_address" placeholder="详细地址" />
        </div>

        <div>
          <label class="muted">收件人 *</label>
          <input v-model="form.receiver_name" placeholder="收件人姓名" />
        </div>
        <div>
          <label class="muted">收件人电话</label>
          <input v-model="form.receiver_phone" placeholder="手机号" />
        </div>
        <div class="full">
          <label class="muted">收件地址</label>
          <input v-model="form.receiver_address" placeholder="详细地址" />
        </div>

        <div>
          <label class="muted">起始网点</label>
          <select v-model="form.origin_branch_id">
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>
        <div>
          <label class="muted">目的网点</label>
          <select v-model="form.dest_branch_id">
            <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>

        <div>
          <label class="muted">司机</label>
          <select v-model="form.driver_id">
            <option :value="null">未指派</option>
            <option v-for="d in drivers" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
        <div>
          <label class="muted">车辆</label>
          <select v-model="form.vehicle_id">
            <option :value="null">未指派</option>
            <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.plate }}</option>
          </select>
        </div>

        <div>
          <label class="muted">货物名称</label>
          <input v-model="form.goods" placeholder="如：电子配件 3 箱" />
        </div>
        <div>
          <label class="muted">重量（kg）</label>
          <input v-model="form.weight_kg" type="number" step="0.1" min="0" />
        </div>

        <div class="full">
          <label class="muted">备注</label>
          <textarea v-model="form.remark" rows="2" placeholder="可选"></textarea>
        </div>
      </div>

      <p v-if="error" class="err">{{ error }}</p>

      <div class="row" style="margin-top: 16px">
        <button class="primary" :disabled="saving">{{ saving ? '提交中…' : '创建运单' }}</button>
        <button type="button" @click="router.back()">取消</button>
      </div>
    </form>
  </div>
</template>
