<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const user = ref(JSON.parse(localStorage.getItem('app_user') || '{}'))
const profile = ref({})
const videos = [
  { title: '干线运输 · 全国公路网络', src: '/promo/highway.mp4', poster: '/promo/highway.jpg' },
  { title: '智慧仓储 · 安全高效分拣', src: '/promo/warehouse.mp4', poster: '/promo/warehouse.jpg' },
  { title: '数据驱动 · 运营实时洞察', src: '/promo/data.mp4', poster: '/promo/data.jpg' },
]
const playing = ref(-1)

const showProfile = ref(false)
const nick = ref('')
const bindModal = ref(false)
const bindKind = ref('phone')     // phone / wechat / qq
const bindPhone = ref('')
const bindCode = ref('')
const bindNick = ref('')
const bindSent = ref('')
const bindBusy = ref(false)
const avatarInput = ref(null)
const toast = ref('')

async function load() {
  try { profile.value = await api.get('/mobile/profile') } catch { /* 401 已拦截 */ }
}
onMounted(load)

function editProfile() {
  nick.value = profile.value.display_name || ''
  showProfile.value = true
}

async function saveProfile() {
  try {
    await api.post('/mobile/profile', { display_name: nick.value })
    toastMsg('昵称已保存')
    showProfile.value = false
    load()
  } catch (e) { toastMsg(e.message) }
}

function pickAvatar() { avatarInput.value.click() }

function onAvatarChange(e) {
  const file = e.target.files[0]
  if (!file) return
  // 前端压缩到 256px 再上传，避免 base64 过大
  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas')
    const s = Math.min(1, 256 / Math.max(img.width, img.height))
    canvas.width = Math.round(img.width * s)
    canvas.height = Math.round(img.height * s)
    canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
    const avatar = canvas.toDataURL('image/jpeg', 0.8)
    api.post('/mobile/profile', { avatar })
      .then(() => { toastMsg('头像已更新'); load() })
      .catch((err) => toastMsg(err.message))
  }
  img.src = URL.createObjectURL(file)
  e.target.value = ''
}

function openBind(kind) {
  bindKind.value = kind
  bindPhone.value = ''
  bindCode.value = ''
  bindNick.value = ''
  bindSent.value = ''
  bindModal.value = true
}

async function sendCode() {
  bindBusy.value = true
  try {
    const data = await api.post('/auth/sms/send', { phone: bindPhone.value })
    bindSent.value = data.demo_code
      ? `演示环境验证码：${data.demo_code}`
      : (data.message || '验证码已发送到手机')
  } catch (e) { toastMsg(e.message) } finally { bindBusy.value = false }
}

async function submitBind() {
  bindBusy.value = true
  try {
    if (bindKind.value === 'phone') {
      await api.post('/mobile/bind/phone', { phone: bindPhone.value, code: bindCode.value })
    } else {
      await api.post('/mobile/bind/social', { kind: bindKind.value, nickname: bindNick.value })
    }
    bindModal.value = false
    toastMsg('绑定成功')
    load()
  } catch (e) { toastMsg(e.message) } finally { bindBusy.value = false }
}

function play(i, e) {
  const v = e.target
  if (playing.value !== i) {
    document.querySelectorAll('video').forEach(x => { x.pause(); x.currentTime = 0 })
    playing.value = i
    v.play().catch(() => {})
  } else { v.pause(); playing.value = -1 }
}

function logout() {
  localStorage.removeItem('app_token')
  localStorage.removeItem('app_user')
  router.replace('/login')
}

function toastMsg(msg) {
  toast.value = msg
  setTimeout(() => toast.value = '', 2400)
}
</script>

<template>
  <div class="page">
    <div class="hero">
      <img v-if="profile.avatar" class="avatar" :src="profile.avatar" @click="pickAvatar" />
      <div v-else class="avatar avatar-txt" @click="pickAvatar">{{ (profile.display_name || user.username || '?')[0] }}</div>
      <input ref="avatarInput" type="file" accept="image/*" style="display:none" @change="onAvatarChange" />
      <h1>{{ profile.display_name || user.username }}</h1>
      <p>点击头像可更换 · 注册于 {{ profile.created_at || '' }}</p>
    </div>

    <div class="card row" @click="editProfile">
      <span>✏️</span><b>修改昵称</b>
      <span class="arrow">{{ profile.display_name || '未设置' }} ›</span>
    </div>
    <div class="card row" @click="openBind('phone')">
      <span>📱</span><b>绑定手机号</b>
      <span class="arrow">{{ profile.bound_phone || '未绑定' }} ›</span>
    </div>
    <div class="card row" @click="openBind('wechat')">
      <span>💚</span><b>绑定微信</b>
      <span class="arrow">{{ profile.bound_wechat || '未绑定' }} ›</span>
    </div>
    <div class="card row" @click="openBind('qq')">
      <span>💙</span><b>绑定 QQ</b>
      <span class="arrow">{{ profile.bound_qq || '未绑定' }} ›</span>
    </div>

    <div class="card row" @click="router.push('/')"><span>📦</span><b>我的快递</b><span class="arrow">›</span></div>
    <div class="card row" @click="router.push('/branches')"><span>🏪</span><b>附近网点 / 寄件</b><span class="arrow">›</span></div>
    <div class="card row" @click="router.push('/mall')"><span>🛍️</span><b>商城购物</b><span class="arrow">›</span></div>

    <div class="sec-head"><b>品牌宣传视频</b><span class="muted">点击播放</span></div>
    <div v-for="(v, i) in videos" :key="v.title" class="card">
      <b style="font-size:14px">{{ v.title }}</b>
      <video style="width:100%;aspect-ratio:16/9;border-radius:10px;margin-top:8px;object-fit:cover;background:#0f172a"
             :src="v.src" :poster="v.poster" muted loop playsinline preload="metadata" @click="play(i, $event)"></video>
    </div>

    <button class="logout" @click="logout">退出登录</button>

    <!-- 昵称弹窗 -->
    <div v-if="showProfile" class="mask" @click.self="showProfile = false">
      <div class="sheet">
        <h3>修改昵称</h3>
        <input class="inp" v-model="nick" maxlength="20" placeholder="输入新昵称" />
        <button class="m-btn" @click="saveProfile">保存</button>
        <button class="ghost" @click="showProfile = false">取消</button>
      </div>
    </div>

    <!-- 绑定弹窗 -->
    <div v-if="bindModal" class="mask" @click.self="bindModal = false">
      <div class="sheet">
        <h3>{{ { phone: '绑定手机号', wechat: '绑定微信', qq: '绑定 QQ' }[bindKind] }}</h3>
        <template v-if="bindKind === 'phone'">
          <input class="inp" v-model="bindPhone" maxlength="11" inputmode="numeric" placeholder="11 位手机号" />
          <div class="code-row">
            <input class="inp" v-model="bindCode" maxlength="6" inputmode="numeric" placeholder="6 位验证码" />
            <button class="send" :disabled="bindBusy || !/^1\d{10}$/.test(bindPhone)" @click="sendCode">获取验证码</button>
          </div>
          <p v-if="bindSent" class="hint">{{ bindSent }}</p>
        </template>
        <template v-else>
          <p class="muted" style="text-align:center;margin:4px 0 10px">演示模式：输入{{ bindKind === 'wechat' ? '微信' : 'QQ' }}昵称完成绑定<br/>接入开放平台后此处为真实扫码授权</p>
          <input class="inp" v-model="bindNick" :placeholder="(bindKind === 'wechat' ? '微信' : 'QQ') + '昵称'" />
        </template>
        <button class="m-btn" :disabled="bindBusy" @click="submitBind">
          {{ bindKind === 'phone' ? '确认绑定' : '完成绑定' }}
        </button>
        <button class="ghost" @click="bindModal = false">取消</button>
      </div>
    </div>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

<style scoped>
.avatar {
  width: 60px; height: 60px; border-radius: 50%;
  object-fit: cover; border: 2px solid rgba(255,255,255,.6);
  margin-bottom: 8px;
}
.avatar-txt {
  background: #fff; color: #2563eb;
  display: flex; align-items: center; justify-content: center;
  font-size: 26px; font-weight: 700;
}
.hero { text-align: center; }
.hero p { font-size: 12px; opacity: .8; }
.row { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.row b { flex: 1; font-size: 15px; }
.row .arrow { color: #9ca3af; font-size: 13px; max-width: 45%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sec-head { display: flex; justify-content: space-between; margin: 4px 2px 10px; }
.logout {
  width: 100%; height: 44px; border-radius: 22px;
  background: #fff; color: #dc2626; margin-top: 16px;
  box-shadow: 0 2px 10px rgba(31,41,55,.06);
}
.mask { position: fixed; inset: 0; background: rgba(15,23,42,.55); display: flex; align-items: flex-end; z-index: 50; }
.sheet { width: 100%; background: #fff; border-radius: 18px 18px 0 0; padding: 20px 18px calc(20px + env(safe-area-inset-bottom)); }
.sheet h3 { margin-bottom: 12px; text-align: center; }
.inp {
  width: 100%; height: 42px; border: 1px solid #e5e7eb; border-radius: 10px;
  padding: 0 12px; font-size: 15px; margin-bottom: 10px;
}
.code-row { display: flex; gap: 10px; }
.code-row .inp { flex: 1; }
.send { width: 110px; border-radius: 10px; background: #eff6ff; color: #2563eb; font-size: 14px; }
.send:disabled { opacity: .5; }
.hint { color: #16a34a; font-size: 13px; margin-bottom: 8px; text-align: center; }
.muted { font-size: 13px; color: #6b7280; }
.m-btn { width: 100%; height: 44px; border-radius: 22px; background: #2563eb; color: #fff; font-size: 15px; margin-bottom: 10px; }
.m-btn:disabled { opacity: .55; }
.ghost { width: 100%; height: 40px; border-radius: 20px; background: #f3f4f6; color: #6b7280; }
</style>
