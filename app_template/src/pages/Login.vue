<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const phone = ref('')
const code = ref('')
const hint = ref('')
const sending = ref(false)
const countdown = ref(0)
let timer = null

async function sendSms() {
  hint.value = ''
  if (!/^1\d{10}$/.test(phone.value)) { hint.value = '请输入正确的 11 位手机号'; return }
  sending.value = true
  try {
    const data = await api.post('/auth/sms/send', { phone: phone.value })
    hint.value = data.demo_code
      ? `验证码：${data.demo_code}（演示环境直接回显）`
      : (data.message || '验证码已发送到你的手机，请查收短信')
    countdown.value = 60
    timer = setInterval(() => { countdown.value--; if (countdown.value <= 0) clearInterval(timer) }, 1000)
  } catch (e) { hint.value = e.message } finally { sending.value = false }
}

async function login() {
  hint.value = ''
  if (!/^1\d{10}$/.test(phone.value)) { hint.value = '请输入正确的 11 位手机号'; return }
  if (!/^\d{6}$/.test(code.value)) { hint.value = '请输入 6 位验证码'; return }
  try {
    const data = await api.post('/auth/phone-login', { phone: phone.value, code: code.value })
    saveAndGo(data)
  } catch (e) { hint.value = e.message }
}

function saveAndGo(data) {
  localStorage.setItem('app_token', data.token)
  localStorage.setItem('app_user', JSON.stringify(data.user))
  router.replace('/')
}

// ---------- 扫码登录（演示模式） ----------
const qrModal = ref(false)
const qrType = ref('wechat')
const qrStatus = ref('loading')
const qrId = ref('')
let pollTimer = null

function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function drawQr(canvasEl, seed) {
  const N = 25, cell = 7
  canvasEl.width = canvasEl.height = N * cell
  const ctx = canvasEl.getContext('2d')
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvasEl.width, canvasEl.height)
  const rand = mulberry32(seed)
  const inFinder = (r, c) => (r < 7 && c < 7) || (r < 7 && c >= N - 7) || (r >= N - 7 && c < 7)
  ctx.fillStyle = qrType.value === 'wechat' ? '#07c160' : '#12b7f5'
  for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) {
    if (!inFinder(r, c) && rand() < 0.45) ctx.fillRect(c * cell, r * cell, cell - 1, cell - 1)
  }
  const finder = (ox, oy) => {
    ctx.fillStyle = '#111'
    ctx.fillRect(ox * cell, oy * cell, 7 * cell, 7 * cell)
    ctx.fillStyle = '#fff'
    ctx.fillRect((ox + 1) * cell, (oy + 1) * cell, 5 * cell, 5 * cell)
    ctx.fillStyle = '#111'
    ctx.fillRect((ox + 2) * cell, (oy + 2) * cell, 3 * cell, 3 * cell)
  }
  finder(0, 0); finder(0, N - 7); finder(N - 7, 0)
}

async function openQr(type) {
  qrType.value = type
  qrStatus.value = 'loading'
  qrModal.value = true
  try {
    const data = await api.post('/auth/qr/create', {})
    qrId.value = data.uuid
    qrStatus.value = 'waiting'
    drawQr(document.getElementById('qr-canvas'), parseInt(data.uuid.slice(0, 8), 16))
    clearInterval(pollTimer)
    pollTimer = setInterval(async () => {
      if (qrStatus.value !== 'waiting') return
      try {
        const s = await api.get(`/auth/qr/poll?uuid=${data.uuid}`)
        if (s.status === 'confirmed') {
          qrStatus.value = 'confirmed'
          clearInterval(pollTimer)
          saveAndGo(s)
          setTimeout(() => qrModal.value = false, 400)
        } else if (s.status === 'expired') {
          qrStatus.value = 'expired'
          clearInterval(pollTimer)
        }
      } catch { /* 下轮重试 */ }
    }, 2000)
  } catch { qrStatus.value = 'expired' }
}

async function mockScan() {
  if (qrStatus.value !== 'waiting') return
  try {
    const data = await api.post(`/auth/qr/confirm?uuid=${qrId.value}`, {})
    qrStatus.value = 'confirmed'
    clearInterval(pollTimer)
    saveAndGo(data)
    setTimeout(() => qrModal.value = false, 400)
  } catch { qrStatus.value = 'expired' }
}
</script>

<template>
  <div class="login-page">
    <div class="logo">🚚</div>
    <h1>智运到家</h1>
    <p class="sub">查快递 · 寄快递 · 一键商城购物</p>

    <div class="card form">
      <input v-model="phone" placeholder="输入 11 位手机号" maxlength="11" inputmode="numeric" />
      <div class="code-row">
        <input v-model="code" placeholder="6 位验证码" maxlength="6" inputmode="numeric" />
        <button class="sms" :disabled="countdown > 0 || sending" @click="sendSms">
          {{ countdown > 0 ? countdown + 's' : '获取验证码' }}
        </button>
      </div>
      <p v-if="hint" class="hint">{{ hint }}</p>
      <button class="primary" @click="login">登录 / 自动注册</button>
    </div>

    <div class="divider"><span>其他方式登录</span></div>
    <div class="oauth">
      <span class="ico wechat" @click="openQr('wechat')">微信</span>
      <span class="ico qq" @click="openQr('qq')">QQ</span>
    </div>

    <div v-if="qrModal" class="mask" @click.self="qrModal = false; clearInterval(pollTimer)">
      <div class="qr-card">
        <h3>{{ qrType === 'wechat' ? '微信扫码登录' : 'QQ 扫码登录' }}</h3>
        <canvas id="qr-canvas" v-show="qrStatus === 'waiting'"></canvas>
        <div v-if="qrStatus === 'loading'" class="st">生成中…</div>
        <div v-if="qrStatus === 'confirmed'" class="st ok">✓ 登录成功</div>
        <div v-if="qrStatus === 'expired'" class="st">二维码已过期</div>
        <p class="demo">演示环境：点击下方按钮模拟手机扫码</p>
        <button class="primary" :disabled="qrStatus !== 'waiting'" @click="mockScan">模拟扫码登录</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background: linear-gradient(160deg, #2563eb 0%, #1e40af 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 12vh;
}
.logo {
  width: 72px; height: 72px; border-radius: 20px;
  background: #fff; font-size: 40px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 20px rgba(0,0,0,.25);
}
h1 { color: #fff; font-size: 24px; margin: 14px 0 4px; letter-spacing: 4px; }
.sub { color: rgba(255,255,255,.8); font-size: 13px; margin-bottom: 26px; }
.form { width: min(340px, 90vw); display: flex; flex-direction: column; gap: 12px; }
.code-row { display: flex; gap: 10px; }
.code-row input { flex: 1; }
.sms {
  width: 110px; border-radius: 10px; background: #eef2ff; color: #2563eb; font-size: 13px;
}
.sms:disabled { opacity: .5; }
.hint { font-size: 12px; color: #059669; background: #ecfdf5; border-radius: 8px; padding: 6px 10px; }
.primary {
  height: 44px; border-radius: 22px; background: #2563eb; color: #fff; font-size: 15px;
}
.primary:disabled { opacity: .55; }
.divider {
  width: min(340px, 90vw);
  display: flex; align-items: center; gap: 12px;
  margin: 24px 0 16px; color: rgba(255,255,255,.7); font-size: 12px;
}
.divider::before, .divider::after { content: ""; flex: 1; height: 1px; background: rgba(255,255,255,.25); }
.oauth { display: flex; gap: 28px; }
.ico {
  width: 46px; height: 46px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 15px; font-weight: 600;
}
.ico.wechat { background: #07c160; }
.ico.qq { background: #12b7f5; }

.mask { position: fixed; inset: 0; background: rgba(0,0,0,.55); display: flex; align-items: center; justify-content: center; z-index: 50; }
.qr-card { width: min(300px, 86vw); background: #fff; border-radius: 14px; padding: 20px; text-align: center; }
.qr-card h3 { font-size: 16px; margin-bottom: 14px; }
.qr-card canvas { width: 180px; height: 180px; }
.st { color: #6b7280; font-size: 13px; padding: 20px 0; }
.st.ok { color: #059669; font-weight: 600; }
.demo { font-size: 12px; color: #d97706; margin: 10px 0; }
</style>
