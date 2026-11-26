<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import api from '../api'

const props = defineProps({ orderId: { type: Number, required: true } })

const el = ref(null)
const loc = ref(null)
const noKey = ref(false)
const error = ref('')
let map = null

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

// 内联 SVG 图标（不引用外部图片）
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

async function init() {
  try {
    const [cfg, data] = await Promise.all([api.get('/map/config'), api.get(`/map/order/${props.orderId}/location`)])
    if (!data.supported) { error.value = data.message; return }
    loc.value = data
    if (!cfg.key) { noKey.value = true; return }

    await loadAMap(cfg.key, cfg.security_jscode)
    const AMap = window.AMap
    map = new AMap.Map(el.value, { zoom: 6, viewMode: '2D' })

    const start = new AMap.Marker({
      position: [data.origin.lng, data.origin.lat],
      icon: new AMap.Icon({ image: ICON_START, size: new AMap.Size(34, 34) }),
      offset: new AMap.Pixel(-17, -17),
      title: `起点：${data.from_city}`,
    })
    const end = new AMap.Marker({
      position: [data.dest.lng, data.dest.lat],
      icon: new AMap.Icon({ image: ICON_END, size: new AMap.Size(34, 34) }),
      offset: new AMap.Pixel(-17, -17),
      title: `终点：${data.to_city}`,
    })
    const truck = new AMap.Marker({
      position: [data.current.lng, data.current.lat],
      icon: new AMap.Icon({ image: ICON_TRUCK, size: new AMap.Size(40, 40) }),
      offset: new AMap.Pixel(-20, -20),
      title: '货物当前位置',
      zIndex: 120,
    })
    // 全程浅色线 + 已走深色线
    const fullLine = new AMap.Polyline({
      path: [[data.origin.lng, data.origin.lat], [data.dest.lng, data.dest.lat]],
      strokeColor: '#c7d2fe', strokeWeight: 4, strokeStyle: 'dashed', strokeOpacity: 0.8,
    })
    const doneLine = new AMap.Polyline({
      path: data.path.map((p) => [p.lng, p.lat]),
      strokeColor: '#6366f1', strokeWeight: 5, strokeOpacity: 0.95, lineJoin: 'round',
    })
    map.add([fullLine, doneLine, start, end, truck])
    map.setFitView([fullLine, start, end], false, [60, 60, 60, 60])
  } catch (e) {
    error.value = e.message
  }
}

onMounted(init)
onBeforeUnmount(() => map && map.destroy())
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
        <span class="muted" style="font-size: 12px; margin-left: auto">运输进度 {{ Math.round(loc.progress * 100) }}%</span>
      </div>
      <div ref="el" class="amap-box"></div>
      <div class="legend">
        <span><i style="background:#16a34a"></i>起点</span>
        <span><i style="background:#ef4444"></i>终点</span>
        <span><i style="background:#6366f1"></i>已运输路线</span>
        <span class="muted">定位每 30 分钟随运单状态自动更新</span>
      </div>
    </template>
  </div>
</template>

<style scoped>
.amap-box { height: 380px; border-radius: 10px; overflow: hidden; border: 1px solid var(--line); }

.loc-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.city { font-size: 14px; font-weight: 600; }
.track { position: relative; flex: 1; max-width: 420px; height: 24px; display: flex; align-items: center; }
.track-line { flex: 1; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; }
.track-line i { display: block; height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6); border-radius: 4px; transition: width .6s; }
.truck-emoji { position: absolute; top: -6px; font-size: 18px; transition: left .6s; }

.legend { display: flex; align-items: center; gap: 18px; margin-top: 10px; font-size: 12px; color: var(--muted); }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; }

.key-guide { background: #f8fafc; border: 1px dashed var(--line); border-radius: 10px; padding: 18px 20px; }
.kg-title { font-weight: 600; margin-bottom: 8px; }
.kg-text { font-size: 13px; color: var(--muted); line-height: 1.9; }
</style>
