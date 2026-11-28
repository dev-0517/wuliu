<script setup>
// 点阵 3D 地球：canvas 2D 正交投影，支持拖拽旋转、滚轮/双指缩放、空闲自转
import { onBeforeUnmount, onMounted, ref } from 'vue'
import LAND from '../globeData'

const props = defineProps({
  markers: { type: Array, default: () => [] }, // [{ name, lon, lat }]
})

const canvas = ref(null)
const state = {
  rotY: -1.6, // 经度偏移（初始对准东亚）
  rotX: -0.35, // 倾角
  scale: 1,
  dragging: false,
  lastX: 0,
  lastY: 0,
  pinchDist: 0,
  pointers: new Map(),
  auto: true,
  raf: 0,
}

function resize() {
  const cv = canvas.value
  const dpr = window.devicePixelRatio || 1
  cv.width = cv.clientWidth * dpr
  cv.height = cv.clientHeight * dpr
  const ctx = cv.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
}

function project(lon, lat) {
  const lo = (lon * Math.PI) / 180 + state.rotY
  const la = (lat * Math.PI) / 180
  let x = Math.cos(la) * Math.sin(lo)
  let y = Math.sin(la)
  let z = Math.cos(la) * Math.cos(lo)
  const cx = Math.cos(state.rotX)
  const sx = Math.sin(state.rotX)
  const y2 = y * cx - z * sx
  const z2 = y * sx + z * cx
  return { x, y: y2, z: z2 }
}

function draw() {
  const cv = canvas.value
  const ctx = cv.getContext('2d')
  const w = cv.clientWidth
  const h = cv.clientHeight
  const cx = w / 2
  const cy = h / 2
  const R = Math.min(w, h) * 0.36 * state.scale
  ctx.clearRect(0, 0, w, h)

  // 大气光晕
  const glow = ctx.createRadialGradient(cx, cy, R * 0.7, cx, cy, R * 1.5)
  glow.addColorStop(0, 'rgba(56,189,248,.18)')
  glow.addColorStop(1, 'rgba(56,189,248,0)')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, w, h)

  // 球体底色
  const ball = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.3, R * 0.1, cx, cy, R)
  ball.addColorStop(0, 'rgba(30,64,124,.9)')
  ball.addColorStop(1, 'rgba(8,20,44,.95)')
  ctx.beginPath()
  ctx.arc(cx, cy, R, 0, Math.PI * 2)
  ctx.fillStyle = ball
  ctx.fill()
  ctx.strokeStyle = 'rgba(96,165,250,.35)'
  ctx.lineWidth = 1
  ctx.stroke()

  // 陆地点阵（只画正面半球）
  for (let i = 0; i < LAND.length; i++) {
    const p = project(LAND[i][0], LAND[i][1])
    if (p.z <= 0.05) continue
    const px = cx + p.x * R
    const py = cy - p.y * R
    ctx.fillStyle = `rgba(125,211,252,${0.25 + p.z * 0.65})`
    ctx.beginPath()
    ctx.arc(px, py, 1.3 * state.scale, 0, Math.PI * 2)
    ctx.fill()
  }

  // 网点标记（脉冲光点 + 名称）
  const now = Date.now() / 1000
  for (const m of props.markers) {
    const p = project(m.lon, m.lat)
    if (p.z <= 0.12) continue
    const px = cx + p.x * R
    const py = cy - p.y * R
    const pulse = (Math.sin(now * 3) + 1) / 2
    ctx.beginPath()
    ctx.arc(px, py, 4 + pulse * 7, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(250,204,21,${0.35 * (1 - pulse) + 0.1})`
    ctx.fill()
    ctx.beginPath()
    ctx.arc(px, py, 3, 0, Math.PI * 2)
    ctx.fillStyle = '#facc15'
    ctx.fill()
    ctx.font = '12px sans-serif'
    ctx.fillStyle = '#fff'
    ctx.fillText(m.name, px + 8, py - 6)
  }

  if (state.auto && !state.dragging) state.rotY += 0.0012
  state.raf = requestAnimationFrame(draw)
}

function onPointerDown(e) {
  state.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
  if (state.pointers.size === 1) {
    state.dragging = true
    state.auto = false
    state.lastX = e.clientX
    state.lastY = e.clientY
  } else if (state.pointers.size === 2) {
    const [a, b] = [...state.pointers.values()]
    state.pinchDist = Math.hypot(a.x - b.x, a.y - b.y)
  }
  canvas.value.setPointerCapture(e.pointerId)
}

function onPointerMove(e) {
  if (!state.pointers.has(e.pointerId)) return
  state.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY })
  if (state.pointers.size === 2) {
    const [a, b] = [...state.pointers.values()]
    const d = Math.hypot(a.x - b.x, a.y - b.y)
    if (state.pinchDist) state.scale = clamp(state.scale * (d / state.pinchDist))
    state.pinchDist = d
  } else if (state.dragging) {
    state.rotY += (e.clientX - state.lastX) * 0.005
    state.rotX = clamp(state.rotX + (e.clientY - state.lastY) * 0.005, -1.2, 1.2)
    state.lastX = e.clientX
    state.lastY = e.clientY
  }
}

function onPointerUp(e) {
  state.pointers.delete(e.pointerId)
  if (state.pointers.size === 0) state.dragging = false
  if (state.pointers.size < 2) state.pinchDist = 0
}

function clamp(v, min = 0.7, max = 2.4) {
  return Math.min(max, Math.max(min, v))
}

function onWheel(e) {
  e.preventDefault()
  state.auto = false
  state.scale = clamp(state.scale * (e.deltaY > 0 ? 0.92 : 1.08))
}

function reset() {
  state.auto = true
}

onMounted(() => {
  resize()
  window.addEventListener('resize', resize)
  const cv = canvas.value
  cv.addEventListener('pointerdown', onPointerDown)
  cv.addEventListener('pointermove', onPointerMove)
  cv.addEventListener('pointerup', onPointerUp)
  cv.addEventListener('pointercancel', onPointerUp)
  cv.addEventListener('wheel', onWheel, { passive: false })
  cv.addEventListener('pointerleave', reset)
  state.raf = requestAnimationFrame(draw)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(state.raf)
  window.removeEventListener('resize', resize)
})
</script>

<template>
  <canvas ref="canvas" class="globe" title="拖拽旋转 · 滚轮/双指缩放"></canvas>
</template>

<style scoped>
.globe {
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: grab;
}
.globe:active { cursor: grabbing; }
</style>
