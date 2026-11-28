<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import WorldGlobe from '../components/WorldGlobe.vue'

const router = useRouter()

// ---------- 账号密码登录 / 注册 ----------
const tab = ref('account') // account | phone
const mode = ref('login') // login | register
const username = ref('')
const password = ref('')
const confirm = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (!username.value.trim() || !password.value) {
    error.value = '请输入账户和密码'
    return
  }
  if (mode.value === 'register' && password.value !== confirm.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    const path = mode.value === 'login' ? '/auth/login' : '/auth/register'
    const data = await api.post(path, { username: username.value.trim(), password: password.value })
    localStorage.setItem('token', data.token)
    localStorage.setItem('user', JSON.stringify(data.user))
    router.push('/')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// ---------- 手机号验证码登录 ----------
const phone = ref('')
const smsCode = ref('')
const smsHint = ref('')
const smsSending = ref(false)
const countdown = ref(0)
let timer = null

function startCountdown() {
  countdown.value = 60
  timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) clearInterval(timer)
  }, 1000)
}
onBeforeUnmount(() => clearInterval(timer))

async function sendSms() {
  smsHint.value = ''
  if (!/^1\d{10}$/.test(phone.value)) {
    smsHint.value = '请输入正确的 11 位手机号'
    return
  }
  smsSending.value = true
  try {
    const data = await api.post('/auth/sms/send', { phone: phone.value })
    smsHint.value = `演示环境未接真实短信，验证码：${data.demo_code}`
    startCountdown()
  } catch (e) {
    smsHint.value = e.message
  } finally {
    smsSending.value = false
  }
}

async function phoneSubmit() {
  smsHint.value = ''
  if (!/^1\d{10}$/.test(phone.value)) {
    smsHint.value = '请输入正确的 11 位手机号'
    return
  }
  if (!/^\d{6}$/.test(smsCode.value)) {
    smsHint.value = '请输入 6 位验证码'
    return
  }
  loading.value = true
  try {
    const data = await api.post('/auth/phone-login', { phone: phone.value, code: smsCode.value })
    localStorage.setItem('token', data.token)
    localStorage.setItem('user', JSON.stringify(data.user))
    router.push('/')
  } catch (e) {
    smsHint.value = e.message
  } finally {
    loading.value = false
  }
}

// ---------- 扫码登录（微信 / QQ，演示模式模拟扫码） ----------
const qrModal = ref(false)
const qrType = ref('wechat') // wechat | qq
const qrUuid = ref('')
const qrStatus = ref('loading') // loading | waiting | confirmed | expired
let pollTimer = null
let pollBusy = false

// 伪二维码绘制：用 uuid 做种子的确定性伪随机点阵 + 三个定位角
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function drawQr(canvasEl, seed) {
  const N = 25
  const cell = 8
  const size = N * cell
  canvasEl.width = size
  canvasEl.height = size
  const ctx = canvasEl.getContext('2d')
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, size, size)
  const rand = mulberry32(seed)
  const inFinder = (r, c) =>
    (r < 7 && c < 7) || (r < 7 && c >= N - 7) || (r >= N - 7 && c < 7)
  ctx.fillStyle = qrType.value === 'wechat' ? '#07c160' : '#12b7f5'
  for (let r = 0; r < N; r++) {
    for (let c = 0; c < N; c++) {
      if (inFinder(r, c)) continue
      if (rand() < 0.45) ctx.fillRect(c * cell, r * cell, cell - 1, cell - 1)
    }
  }
  // 三个定位角
  const finder = (ox, oy) => {
    ctx.fillStyle = '#111'
    ctx.fillRect(ox * cell, oy * cell, 7 * cell, 7 * cell)
    ctx.fillStyle = '#fff'
    ctx.fillRect((ox + 1) * cell, (oy + 1) * cell, 5 * cell, 5 * cell)
    ctx.fillStyle = '#111'
    ctx.fillRect((ox + 2) * cell, (oy + 2) * cell, 3 * cell, 3 * cell)
  }
  finder(0, 0)
  finder(0, N - 7)
  finder(N - 7, 0)
}

async function openQr(type) {
  qrType.value = type
  qrUuid.value = ''
  qrStatus.value = 'loading'
  qrModal.value = true
  try {
    const data = await api.post('/auth/qr/create', {})
    qrUuid.value = data.uuid
    qrStatus.value = 'waiting'
    drawQr(document.getElementById('qr-canvas'), parseInt(data.uuid.slice(0, 8), 16))
    startPoll()
  } catch (e) {
    qrStatus.value = 'expired'
  }
}

function startPoll() {
  clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    if (!qrUuid.value || qrStatus.value !== 'waiting' || pollBusy) return
    pollBusy = true
    try {
      const data = await api.get(`/auth/qr/poll?uuid=${qrUuid.value}`)
      if (data.status === 'confirmed') {
        qrStatus.value = 'confirmed'
        localStorage.setItem('token', data.token)
        localStorage.setItem('user', JSON.stringify(data.user))
        clearInterval(pollTimer)
        setTimeout(() => router.push('/'), 600)
      } else if (data.status === 'expired') {
        qrStatus.value = 'expired'
        clearInterval(pollTimer)
      }
    } catch { /* 轮询失败忽略，下轮重试 */ } finally {
      pollBusy = false
    }
  }, 2000)
}

async function mockScan() {
  if (!qrUuid.value || qrStatus.value !== 'waiting') return
  try {
    await api.post(`/auth/qr/confirm?uuid=${qrUuid.value}`, {})
  } catch (e) {
    qrStatus.value = 'expired'
  }
}

function closeQr() {
  qrModal.value = false
  clearInterval(pollTimer)
}

const markers = [
  { name: '杭州', lon: 120.15, lat: 30.28 },
  { name: '上海', lon: 121.47, lat: 31.23 },
  { name: '南京', lon: 118.78, lat: 32.06 },
]
</script>

<template>
  <div class="login-page">
    <!-- 3D 地球背景 -->
    <div class="globe-wrap">
      <WorldGlobe :markers="markers" />
      <p class="globe-tip">拖拽旋转 · 滚轮 / 双指缩放</p>
    </div>

    <h1 class="login-title">智慧物流全球通</h1>

    <div class="login-card">
      <!-- 登录方式 Tab -->
      <div class="tabs">
        <span :class="{ on: tab === 'account' }" @click="tab = 'account'; error = ''">账号登录</span>
        <span :class="{ on: tab === 'phone' }" @click="tab = 'phone'">手机号登录</span>
      </div>

      <!-- 账号密码 -->
      <form v-if="tab === 'account'" class="login-form" @submit.prevent="submit">
        <input v-model="username" class="login-input" placeholder="输入您的账户" autocomplete="username" />
        <input v-model="password" class="login-input" type="password" placeholder="输入您的密码" autocomplete="current-password" />
        <input v-if="mode === 'register'" v-model="confirm" class="login-input" type="password" placeholder="再次输入密码" autocomplete="new-password" />
        <p v-if="error" class="login-err">{{ error }}</p>
        <button class="login-btn" :disabled="loading">
          {{ loading ? '提交中…' : mode === 'login' ? '登 录' : '注 册' }}
        </button>
        <p class="login-switch">
          <span>{{ mode === 'login' ? '还没有账号？' : '已有账号？' }}</span>
          <a @click.prevent="mode = mode === 'login' ? 'register' : 'login'; error = ''">
            {{ mode === 'login' ? '立即注册' : '去登录' }}
          </a>
        </p>
      </form>

      <!-- 手机号验证码 -->
      <form v-else class="login-form" @submit.prevent="phoneSubmit">
        <input v-model="phone" class="login-input" placeholder="输入 11 位手机号" maxlength="11" inputmode="numeric" />
        <div class="code-row">
          <input v-model="smsCode" class="login-input" placeholder="6 位验证码" maxlength="6" inputmode="numeric" />
          <button type="button" class="sms-btn" :disabled="countdown > 0 || smsSending" @click="sendSms">
            {{ countdown > 0 ? countdown + 's' : '获取验证码' }}
          </button>
        </div>
        <p v-if="smsHint" class="sms-hint">{{ smsHint }}</p>
        <button class="login-btn" :disabled="loading">
          {{ loading ? '登录中…' : '登录 / 自动注册' }}
        </button>
      </form>

      <!-- 其他登录方式 -->
      <div class="divider"><span>其他方式登录</span></div>
      <div class="other-login">
        <div class="oauth-item" @click="openQr('wechat')">
          <span class="oauth-icon wechat">微</span>
          <span>微信</span>
        </div>
        <div class="oauth-item" @click="openQr('qq')">
          <span class="oauth-icon qq">Q</span>
          <span>QQ</span>
        </div>
      </div>
    </div>

    <!-- 扫码登录弹窗 -->
    <div v-if="qrModal" class="qr-mask" @click.self="closeQr">
      <div class="qr-card">
        <span class="qr-close" @click="closeQr">×</span>
        <h3>{{ qrType === 'wechat' ? '微信扫码登录' : 'QQ 扫码登录' }}</h3>
        <div class="qr-box">
          <canvas id="qr-canvas" v-show="qrStatus === 'waiting'"></canvas>
          <div v-if="qrStatus === 'loading'" class="qr-state">生成中…</div>
          <div v-if="qrStatus === 'confirmed'" class="qr-state ok">✓ 扫码成功，正在进入系统…</div>
          <div v-if="qrStatus === 'expired'" class="qr-state">二维码已过期，请关闭重试</div>
        </div>
        <p class="qr-tip">请使用{{ qrType === 'wechat' ? '微信' : 'QQ' }}扫一扫</p>
        <p class="qr-demo">演示环境未接微信/QQ 开放平台，点击下方按钮模拟手机扫码</p>
        <button class="login-btn" :disabled="qrStatus !== 'waiting'" @click="mockScan">模拟扫码登录</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background: radial-gradient(ellipse at center, #0b1e3d 0%, #060d1d 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  overflow: hidden;
}

.globe-wrap {
  position: absolute;
  inset: 0;
  opacity: .9;
}
.globe-tip {
  position: absolute;
  bottom: 16px;
  left: 0;
  right: 0;
  text-align: center;
  color: rgba(148, 163, 184, .8);
  font-size: 12px;
  pointer-events: none;
}

.login-title {
  margin: 6vh 0 0;
  font-size: 40px;
  font-weight: 700;
  letter-spacing: 10px;
  color: #fff;
  text-shadow: 0 2px 14px rgba(0, 0, 0, .45);
  position: relative;
  z-index: 1;
}

.login-card {
  margin: auto;
  width: min(360px, 88vw);
  background: rgba(255, 255, 255, .96);
  border-radius: 14px;
  padding: 22px 26px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, .35);
  position: relative;
  z-index: 1;
}

.tabs {
  display: flex;
  gap: 22px;
  margin-bottom: 18px;
  border-bottom: 1px solid #e5e7eb;
}
.tabs span {
  padding: 8px 2px;
  font-size: 15px;
  color: #6b7280;
  cursor: pointer;
  border-bottom: 2px solid transparent;
}
.tabs span.on {
  color: #2563eb;
  font-weight: 600;
  border-bottom-color: #2563eb;
}

.login-form {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  width: 100%;
}

.login-input {
  width: 100%;
  height: 42px;
  border: 1px solid #e5e7eb;
  border-radius: 21px;
  background: #fff;
  text-align: center;
  font-size: 14px;
  color: #333;
}
.login-input::placeholder { color: #9ca3af; }
.login-input:focus { outline: 2px solid rgba(37, 99, 235, .55); }

.code-row { display: flex; gap: 10px; width: 100%; }
.code-row .login-input { flex: 1; }
.sms-btn {
  width: 118px;
  height: 42px;
  border: none;
  border-radius: 21px;
  background: #eef2ff;
  color: #2563eb;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.sms-btn:disabled { opacity: .55; cursor: not-allowed; }

.sms-hint {
  margin: 0;
  width: 100%;
  font-size: 12px;
  color: #059669;
  background: #ecfdf5;
  border-radius: 8px;
  padding: 6px 10px;
}

.login-btn {
  width: 100%;
  height: 42px;
  border: none;
  border-radius: 21px;
  background: #2563eb;
  color: #fff;
  font-size: 15px;
  letter-spacing: 4px;
  cursor: pointer;
}
.login-btn:hover { background: #1d4ed8; }
.login-btn:disabled { opacity: .6; cursor: not-allowed; }

.login-err {
  margin: 0;
  color: #dc2626;
  font-size: 13px;
}

.login-switch { margin: 0; font-size: 13px; color: #6b7280; }
.login-switch a { color: #2563eb; font-weight: 600; cursor: pointer; margin-left: 4px; }

.divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 18px 0 12px;
  color: #9ca3af;
  font-size: 12px;
}
.divider::before, .divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: #e5e7eb;
}

.other-login { display: flex; justify-content: center; gap: 40px; padding-bottom: 6px; }
.oauth-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: #6b7280;
  cursor: pointer;
}
.oauth-item:hover { color: #2563eb; }
.oauth-icon {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: 700;
}
.oauth-icon.wechat { background: #07c160; }
.oauth-icon.qq { background: #12b7f5; }

/* 扫码弹窗 */
.qr-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, .55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.qr-card {
  width: min(320px, 88vw);
  background: #fff;
  border-radius: 14px;
  padding: 22px;
  text-align: center;
  position: relative;
}
.qr-close {
  position: absolute;
  top: 10px;
  right: 16px;
  font-size: 22px;
  color: #9ca3af;
  cursor: pointer;
}
.qr-card h3 { margin: 0 0 14px; font-size: 16px; }
.qr-box {
  width: 200px;
  height: 200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.qr-box canvas { width: 200px; height: 200px; }
.qr-state {
  font-size: 13px;
  color: #6b7280;
  padding: 12px;
}
.qr-state.ok { color: #059669; font-size: 15px; font-weight: 600; }
.qr-tip { margin: 12px 0 4px; font-size: 14px; }
.qr-demo { margin: 0 0 14px; font-size: 12px; color: #d97706; }

@media (max-width: 700px) {
  .login-title { font-size: 26px; letter-spacing: 5px; margin-top: 5vh; }
  .login-card { margin-top: 18px; }
}
</style>
