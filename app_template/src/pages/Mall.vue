<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'

const products = ref([])
const toast = ref('')
const buying = ref(0)

// 支付弹窗状态
const payModal = ref(false)
const payProduct = ref(null)
const payOrder = ref(null)      // { order_id, amount }
const payMethod = ref('wechat')
const payQr = ref('')
const payStep = ref('pick')     // pick=选支付方式 / qr=扫码付款 / done=已提交
const payBusy = ref(false)
const myPays = ref([])

async function load() {
  products.value = await api.get('/mobile/products')
}
onMounted(load)

async function buy(p) {
  buying.value = p.id
  try {
    const data = await api.post(`/mobile/buy/${p.id}`, {})
    payProduct.value = p
    payOrder.value = data
    payStep.value = 'pick'
    payModal.value = true
    refreshPays()
  } catch (e) { toastMsg(e.message) } finally { buying.value = 0 }
}

async function chooseMethod(m) {
  payMethod.value = m
  payBusy.value = true
  try {
    const data = await api.post(`/mobile/pay/${payOrder.value.order_id}`, { method: m })
    payQr.value = data.qr
    payOrder.value = { ...payOrder.value, payment_id: data.payment_id, amount: data.amount }
    payStep.value = 'qr'
  } catch (e) { toastMsg(e.message) } finally { payBusy.value = false }
}

async function confirmPaid() {
  payBusy.value = true
  try {
    await api.post(`/mobile/pay-confirm/${payOrder.value.payment_id}`, {})
    payStep.value = 'done'
    refreshPays()
  } catch (e) { toastMsg(e.message) } finally { payBusy.value = false }
}

async function refreshPays() {
  try { myPays.value = await api.get('/mobile/my-payments') } catch { /* ignore */ }
}
refreshPays()

function toastMsg(msg) {
  toast.value = msg
  setTimeout(() => toast.value = '', 2400)
}

function methodLabel(m) { return m === 'wechat' ? '微信支付' : '支付宝' }
function statusLabel(s) { return { paid: '审核中', approved: '已发货', rejected: '已驳回' }[s] || s }
</script>

<template>
  <div class="page">
    <div class="hero">
      <h1>智运商城</h1>
      <p>真实扫码付款 · 后台审核通过后立即派发货物</p>
    </div>

    <div class="grid">
      <div v-for="p in products" :key="p.id" class="card prod">
        <img v-if="p.image" class="thumb" :src="p.image" :alt="p.name" loading="lazy" />
        <div v-else class="thumb thumb-emoji" :style="{ background: p.color }">{{ p.emoji }}</div>
        <b class="name">{{ p.name }}</b>
        <div class="muted desc">{{ p.desc }}</div>
        <div class="foot">
          <span class="price">¥{{ p.price }}</span>
          <button class="buy" :disabled="buying === p.id" @click="buy(p)">
            {{ buying === p.id ? '下单中…' : '购买' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 我的支付记录 -->
    <div v-if="myPays.length" class="pays">
      <div class="sec-head"><b>支付记录</b></div>
      <div v-for="r in myPays" :key="r.id" class="card pay-row">
        <div>
          <b>{{ r.goods }}</b>
          <div class="muted">{{ r.created_at }} · {{ methodLabel(r.method) }}</div>
        </div>
        <div class="right">
          <span class="price">¥{{ r.amount }}</span>
          <span class="p-status" :class="r.status">{{ statusLabel(r.status) }}</span>
        </div>
      </div>
    </div>

    <!-- 支付弹窗 -->
    <div v-if="payModal" class="mask" @click.self="payModal = false">
      <div class="sheet">
        <template v-if="payStep === 'pick'">
          <h3>选择支付方式</h3>
          <p class="muted">{{ payProduct?.name }} · <b class="price">¥{{ payOrder?.amount }}</b></p>
          <button class="m-btn wechat" :disabled="payBusy" @click="chooseMethod('wechat')">💚 微信支付</button>
          <button class="m-btn alipay" :disabled="payBusy" @click="chooseMethod('alipay')">💙 支付宝支付</button>
          <button class="ghost" @click="payModal = false">取消</button>
        </template>

        <template v-else-if="payStep === 'qr'">
          <h3>{{ methodLabel(payMethod) }}扫码付款</h3>
          <img class="qr" :src="payQr" alt="收款码" />
          <p class="muted">请截图或用另一台手机扫描上方收款码<br/>支付金额：<b class="price">¥{{ payOrder?.amount }}</b>，付款后点击下方按钮</p>
          <button class="m-btn" :disabled="payBusy" @click="confirmPaid">我已完成支付</button>
          <button class="ghost" @click="payModal = false">稍后再付</button>
        </template>

        <template v-else>
          <h3>🎉 支付记录已提交</h3>
          <p class="muted">管理员审核通过后货物将立即派发<br/>可在「快递」页查看物流，审核结果见下方支付记录</p>
          <button class="m-btn" @click="payModal = false">知道了</button>
        </template>
      </div>
    </div>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<style scoped>
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.prod { padding: 12px; margin-bottom: 0; }
.thumb {
  aspect-ratio: 1/1; width: 100%; border-radius: 10px;
  object-fit: cover; display: block; margin-bottom: 8px; background: #f3f4f6;
}
.thumb-emoji { display: flex; align-items: center; justify-content: center; font-size: 46px; }
.name { font-size: 14px; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.desc { margin: 3px 0 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.foot { display: flex; justify-content: space-between; align-items: center; }
.price { color: #dc2626; font-weight: 700; font-size: 16px; }
.buy {
  background: #2563eb; color: #fff; border-radius: 14px;
  padding: 5px 16px; font-size: 13px;
}
.buy:disabled { opacity: .55; }
.pays { margin-top: 16px; }
.sec-head { display: flex; justify-content: space-between; margin: 4px 2px 10px; }
.pay-row { display: flex; justify-content: space-between; align-items: center; padding: 12px 14px; }
.pay-row b { font-size: 14px; }
.right { text-align: right; }
.p-status { display: block; font-size: 12px; margin-top: 2px; }
.p-status.paid { color: #b45309; }
.p-status.approved { color: #16a34a; }
.p-status.rejected { color: #dc2626; }
.mask { position: fixed; inset: 0; background: rgba(15,23,42,.55); display: flex; align-items: flex-end; z-index: 50; }
.sheet {
  width: 100%; background: #fff; border-radius: 18px 18px 0 0;
  padding: 20px 18px calc(20px + env(safe-area-inset-bottom));
}
.sheet h3 { margin-bottom: 6px; text-align: center; }
.sheet .muted { text-align: center; margin-bottom: 14px; line-height: 1.6; }
.qr { width: 200px; display: block; margin: 4px auto 10px; border-radius: 10px; border: 1px solid #e5e7eb; }
.m-btn { width: 100%; height: 44px; border-radius: 22px; background: #2563eb; color: #fff; font-size: 15px; margin-bottom: 10px; }
.m-btn.wechat { background: #06c160; }
.m-btn.alipay { background: #1677ff; }
.m-btn:disabled { opacity: .55; }
.ghost { width: 100%; height: 40px; border-radius: 20px; background: #f3f4f6; color: #6b7280; }
</style>
