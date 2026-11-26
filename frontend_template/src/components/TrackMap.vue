<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '../api'

const props = defineProps({ orderId: { type: Number, required: true } })

const el = ref(null)
const loc = ref(null)
const noKey = ref(false)
const error = ref('')
const vias = ref([])          // 途经点时间轴 [{name, ratio, passed, time}]
const etaText = ref('')       // 预计到达文案
const toasts = ref([])        // 动态提示 [{id, text}]
const POLL_MS = 30000

let map = null
let truck = null
let doneLine = null
let routePts = null           // 真实路线折线 [[lng,lat],...]（失败为 null，用直线）
let routeDistanceM = 0        // 真实驾驶总里程（米）
let lastProgress = 0
let arrivedNotified = false
let timer = null
let toastSeq = 0

const labels = { pending: '待揽收', picked: '已揽收', transit: '运输中', delivered: '已签收', exception: '异常' }

function loadAMap(key, jscode) {
  return new Promise((resolve, reject) => {
    if (window.AMap) return resolve()
    window._AMapSecurityConfig = { securityJsCode: jscode }
    const s = document.createElement('script')
    s.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}`
    s.onload = () => (window.AMap ? resolve() : reject(new Error('高德地图加载失败')))
    s.onerror = () => reject(new Error('高德地图脚本加载失败，请检查网络'))
    document.head.appendChild(s)
  })
}

const svgIcon = (svg, w = 34) =>
  `data:image/svg+xml,` + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${w}" viewBox="0 0 48 48">${svg}</svg>`)

const ICON_TRUCK = svgIcon(
  '<rect x="6" y="16" width="22" height="16" rx="2" fill="#6366f1"/><path d="M28 20h8l6 7v5h-14z" fill="#818cf8"/><circle cx="14" cy="36" r="4" fill="#334155"/><circle cx="34" cy="36" r="4" fill="#334155"/><rect x="8" y="19" width="10" height="4" rx="1" fill="#c7d2fe"/>'
)
const ICON_START = svgIcon(
  '<circle cx="24" cy="24" r="20" fill="#16a34a" opacity=".92"/><path d="M15 24l6 6 12-12" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
)
const ICON_END = svgIcon(
  '<circle cx="24" cy="24" r="20" fill="#ef4444" opacity=".92"/><path d="M17 17l14 14M31 17L17 31" stroke="#fff" stroke-width="5" stroke-linecap="round"/>'
)

function toast(text, ms = 6000) {
  const id = ++toastSeq
  toasts.value.push({ id, text })
  setTimeout(() => { toasts.value = toasts.value.filter((t) => t.id !== id) }, ms)
}

// ---------- 真实驾车路线规划（带超时兜底，失败退回直线） ----------
function planRoute(origin, dest) {
  const search = () => new Promise((resolve) => {
    try {
      window.AMap.plugin('AMap.Driving', () => {
        try {
          const driving = new window.AMap.Driving({ policy: 2 }) // 2 = 距离最短
          driving.search(
            new window.AMap.LngLat(origin.lng, origin.lat),
            new window.AMap.LngLat(dest.lng, dest.lat),
            (status, result) => {
              if (status !== 'complete' || !result.routes?.length) return resolve(null)
              const route = result.routes[0]
              const points = []
              const steps = []
              let cumM = 0
              for (const step of route.steps) {
                const start = step.path[0]
                steps.push({ name: step.road || '无名道路', ratio: route.distance ? cumM / route.distance : 0 })
                for (const p of step.path) points.push([p.lng, p.lat])
                cumM += Number(step.distance) || 0
              }
              resolve({ points, distanceM: Number(route.distance) || cumM, steps })
            }
          )
        } catch { resolve(null) }
      })
    } catch { resolve(null) }
  })
  return Promise.race([search(), new Promise((r) => setTimeout(() => r(null), 8000))])
}

// 沿折线按 progress 取当前位置（欧氏长度近似里程）
function alongRoute(points, progress) {
  if (!points || points.length < 2) return null
  let total = 0
  const segs = []
  for (let i = 1; i < points.length; i++) {
    const dx = points[i][0] - points[i - 1][0], dy = points[i][1] - points[i - 1][1]
    const len = Math.sqrt(dx * dx + dy * dy)
    segs.push(len)
    total += len
  }
  let target = total * Math.min(progress, 1)
  for (let i = 0; i < segs.length; i++) {
    if (target <= segs[i]) {
      const t = segs[i] ? target / segs[i] : 0
      return {
        lng: points[i][0] + (points[i + 1][0] - points[i][0]) * t,
        lat: points[i][1] + (points[i + 1][1] - points[i][1]) * t,
        prefix: points.slice(0, i + 2),
      }
    }
    target -= segs[i]
  }
  const last = points[points.length - 1]
  return { lng: last[0], lat: last[1], prefix: points }
}

function fmtTime(min) {
  const d = new Date(Date.now() + min * 60000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function buildVias(data, steps, totalMin) {
  // 取路名变化的关键途经点，最多 8 个
  const list = []
  let lastRoad = ''
  for (const s of steps) {
    if (!s.name || s.name === '无名道路' || s.name === lastRoad || s.ratio >= 0.98) continue
    if (s.name.includes('高速') || list.length < 4) {
      list.push({ name: s.name, ratio: s.ratio })
      lastRoad = s.name
    }
  }
  vias.value = list.slice(0, 8).map((v) => ({
    ...v,
    passed: data.progress >= v.ratio,
    time: data.progress >= v.ratio ? '已通过' : fmtTime((v.ratio - data.progress) * totalMin),
  }))
}

function updateEta(data, totalMin) {
  if (data.arrived) etaText.value = `已到达 ${data.to_city}`
  else etaText.value = `预计 ${fmtTime((1 - data.progress) * totalMin)} 到达 ${data.to_city} · 剩余 ${Math.round((1 - data.progress) * (routeDistanceM / 1000))} km`
}

async function applyLocation(data, first = false) {
  loc.value = data
  if (!map) return

  let cur = { lng: data.current.lng, lat: data.current.lat, prefix: null }
  if (routePts) {
    cur = alongRoute(routePts, data.progress) || cur
  }

  if (first) {
    const full = routePts || [[data.origin.lng, data.origin.lat], [data.dest.lng, data.dest.lat]]
    const AMap = window.AMap
    map.add([
      new AMap.Polyline({ path: full, strokeColor: '#c7d2fe', strokeWeight: 4, strokeStyle: 'dashed', strokeOpacity: 0.85 }),
      new AMap.Marker({ position: [data.origin.lng, data.origin.lat], icon: new AMap.Icon({ image: ICON_START, size: new AMap.Size(34, 34) }), offset: new AMap.Pixel(-17, -17), title: `起点：${data.from_city}` }),
      new AMap.Marker({ position: [data.dest.lng, data.dest.lat], icon: new AMap.Icon({ image: ICON_END, size: new AMap.Size(34, 34) }), offset: new AMap.Pixel(-17, -17), title: `终点：${data.to_city}` }),
    ])
    doneLine = new AMap.Polyline({ path: [], strokeColor: '#6366f1', strokeWeight: 5, strokeOpacity: 0.95, lineJoin: 'round', showDir: true })
    truck = new AMap.Marker({ position: [cur.lng, cur.lat], icon: new AMap.Icon({ image: ICON_TRUCK, size: new AMap.Size(40, 40) }), offset: new AMap.Pixel(-20, -20), title: '货物当前位置', zIndex: 120 })
    map.add([doneLine, truck])
    map.setFitView(map.getAllOverlays(), false, [60, 60, 60, 60])
  }

  const prefix = cur.prefix || (routePts ? alongRoute(routePts, data.progress)?.prefix : null) || [[data.origin.lng, data.origin.lat], [cur.lng, cur.lat]]
  doneLine?.setPath(prefix)
  truck?.setPosition([cur.lng, cur.lat])

  const totalMin = (routeDistanceM / 1000) / 65 * 60 || (data.eta_minutes || 60)
  updateEta(data, totalMin)
  if (routePts && routeSteps.length) buildVias(data, routeSteps, totalMin)

  // 到达 / 途经点动态提示（首次打开不弹历史提示）
  if (!first) {
    if (data.arrived && !arrivedNotified) {
      arrivedNotified = true
      toast(`🎉 货物已到达 ${data.to_city}，运单签收完成！`, 10000)
    } else if (!data.arrived) {
      for (const v of vias.value) {
        if (v.ratio > lastProgress && v.ratio <= data.progress) {
          toast(`📦 已经过 ${v.name}（${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}）`)
        }
      }
    }
  }
  lastProgress = data.progress
}

let routeSteps = []

async function init() {
  try {
    const [cfg, data] = await Promise.all([api.get('/map/config'), api.get(`/map/order/${props.orderId}/location`)])
    if (!data.supported) { error.value = data.message; return }
    lastProgress = data.progress
    arrivedNotified = data.arrived
    if (!cfg.key) { noKey.value = true; loc.value = data; return }

    await loadAMap(cfg.key, cfg.security_jscode)
    // 先渲染地图容器（模板中 div 依赖 loc），再初始化地图
    loc.value = data
    await nextTick()
    map = new window.AMap.Map(el.value, { zoom: 6, center: [data.current.lng, data.current.lat], viewMode: '2D' })
    const route = await planRoute(data.origin, data.dest)
    if (route) {
      routePts = route.points
      routeDistanceM = route.distanceM
      routeSteps = route.steps
    }
    await applyLocation(data, true)

    timer = setInterval(async () => {
      try {
        const fresh = await api.get(`/map/order/${props.orderId}/location`)
        await applyLocation(fresh)
      } catch { /* 轮询失败忽略 */ }
    }, POLL_MS)
  } catch (e) {
    error.value = e.message
  }
}

onMounted(init)
onBeforeUnmount(() => { timer && clearInterval(timer); map && map.destroy() })
</script>

<template>
  <div class="panel">
    <h3 style="margin: 0 0 12px; font-size: 14px">实时货物定位</h3>

    <p v-if="error" class="muted" style="font-size: 13px">{{ error }}</p>

    <template v-else-if="noKey">
      <div class="key-guide">
        <div class="kg-title">🗺️ 地图尚未配置</div>
        <div class="kg-text">
          需要一个免费的高德开放平台 Key 即可启用实时定位：<br />
          1. 访问 <b>lbs.amap.com</b> 注册 / 登录开发者账号<br />
          2. 控制台 → 应用管理 → 创建新应用 → 添加 Key，服务平台选 <b>Web端(JS API)</b><br />
          3. 将 Key 与安全密钥填入后端 <b>.env</b> 的 AMAP_KEY / AMAP_SECURITY_JSCODE 并重启服务
        </div>
      </div>
    </template>

    <template v-else-if="loc">
      <div class="loc-bar">
        <span class="city">{{ loc.from_city }}</span>
        <div class="track">
          <div class="track-line"><i :style="{ width: Math.round(loc.progress * 100) + '%' }"></i></div>
          <span class="truck-emoji" :style="{ left: `calc(${Math.round(loc.progress * 100)}% - 12px)` }">🚚</span>
        </div>
        <span class="city">{{ loc.to_city }}</span>
        <span class="badge" :class="loc.status" style="margin-left: 12px">{{ labels[loc.status] }}</span>
        <span class="eta" :class="{ done: loc.arrived }">{{ etaText }}</span>
      </div>
      <div class="map-wrap">
        <div ref="el" class="amap-box"></div>
        <div v-for="t in toasts" :key="t.id" class="toast">{{ t.text }}</div>
      </div>
      <div class="legend">
        <span><i style="background:#16a34a"></i>起点</span>
        <span><i style="background:#ef4444"></i>终点</span>
        <span><i style="background:#6366f1"></i>已运输路线</span>
        <span class="muted">每 30 秒自动刷新，经过途经点 / 到达时自动提示</span>
      </div>

      <div v-if="vias.length" class="via-panel">
        <div class="via-title">途经点时间提示</div>
        <div class="via-list">
          <div v-for="(v, i) in vias" :key="i" class="via-item" :class="{ passed: v.passed }">
            <span class="via-dot"></span>
            <span class="via-name">{{ v.name }}</span>
            <span class="via-time">{{ v.passed ? '✓ 已通过' : `预计 ${v.time} 经过` }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.map-wrap { position: relative; }
.amap-box { height: 380px; border-radius: 10px; overflow: hidden; border: 1px solid var(--line); }

.toast {
  position: absolute; top: 14px; left: 50%; transform: translateX(-50%);
  background: rgba(30, 35, 60, .92); color: #fff; font-size: 13px;
  padding: 10px 18px; border-radius: 999px; white-space: nowrap; z-index: 200;
  box-shadow: 0 4px 16px rgba(0,0,0,.25);
}

.loc-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.city { font-size: 14px; font-weight: 600; }
.track { position: relative; flex: 1; max-width: 360px; height: 24px; display: flex; align-items: center; }
.track-line { flex: 1; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }
.track-line i { display: block; height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6); border-radius: 4px; transition: width .6s; }
.truck-emoji { position: absolute; top: -6px; font-size: 18px; transition: left .6s; }
.eta { margin-left: auto; font-size: 13px; font-weight: 600; color: var(--primary); }
.eta.done { color: var(--ok); }

.legend { display: flex; align-items: center; gap: 18px; margin-top: 10px; font-size: 12px; color: var(--muted); }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }

.via-panel { margin-top: 14px; background: #f8fafc; border: 1px solid var(--line); border-radius: 10px; padding: 12px 16px; }
.via-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.via-list { display: flex; flex-direction: column; }
.via-item { display: flex; align-items: center; gap: 10px; font-size: 13px; padding: 5px 0; color: var(--muted); }
.via-item.passed { color: var(--text); }
.via-dot { width: 8px; height: 8px; border-radius: 50%; background: #cbd5e1; flex-shrink: 0; }
.via-item.passed .via-dot { background: var(--primary); }
.via-name { flex: 1; }
.via-time { font-size: 12px; }

.key-guide { background: #f8fafc; border: 1px dashed var(--line); border-radius: 10px; padding: 18px 20px; }
.kg-title { font-weight: 600; margin-bottom: 8px; }
.kg-text { font-size: 13px; color: var(--muted); line-height: 1.9; }
</style>
