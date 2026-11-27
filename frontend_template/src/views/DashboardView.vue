<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'
import { truckImage } from '../trucks'

const stats = ref(null)
const error = ref('')
const now = new Date()

// 品牌宣传视频（免费素材 Coverr，悬停播放）
const promos = [
  { title: '干线运输', desc: '全国公路网络 · 干线高效直达', src: '/promo/highway.mp4', poster: '/promo/highway.jpg' },
  { title: '智慧仓储', desc: '标准化仓储作业 · 安全高效分拣', src: '/promo/warehouse.mp4', poster: '/promo/warehouse.jpg' },
  { title: '数据驱动', desc: '运营数据实时洞察 · 决策有据可依', src: '/promo/data.mp4', poster: '/promo/data.jpg' },
]

function playVideo(e) {
  const v = e.currentTarget.querySelector('video')
  if (v) v.play().catch(() => {})
}

function stopVideo(e) {
  const v = e.currentTarget.querySelector('video')
  if (v) { v.pause(); v.currentTime = 0 }
}


const labels = {
  pending: '待揽收',
  picked: '已揽收',
  transit: '运输中',
  delivered: '已签收',
  exception: '异常'
}

const cardColors = {
  pending: { bg: '#fef2f2', dot: '#dc2626' },
  picked: { bg: '#eff6ff', dot: '#2563eb' },
  transit: { bg: '#f0fdf4', dot: '#16a34a' },
  delivered: { bg: '#f5f3ff', dot: '#7c3aed' },
  exception: { bg: '#fffbeb', dot: '#d97706' }
}
const barColors = { pending: '#f59e0b', picked: '#2563eb', transit: '#16a34a', delivered: '#8b5cf6', exception: '#ef4444' }
const dotColors = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444']

const todayCards = computed(() => {
  if (!stats.value) return []
  const t = stats.value.today_by_status || {}
  return ['pending', 'picked', 'transit', 'delivered', 'exception']
    .map(s => ({ key: s, label: labels[s], count: t[s] || 0 }))
})

const statusBars = computed(() => {
  if (!stats.value) return []
  const b = stats.value.by_status || {}
  const total = stats.value.total_orders || 1
  return ['transit', 'pending', 'picked', 'delivered', 'exception']
    .map(s => ({ key: s, label: labels[s], count: b[s] || 0, pct: Math.round((b[s] || 0) / total * 100) }))
})

const maxTrend = computed(() => Math.max(1, ...(stats.value?.trend || []).map(t => t.count)))

const calendarCells = computed(() => {
  if (!stats.value) return []
  const first = new Date(now.getFullYear(), now.getMonth(), 1)
  const days = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
  const lead = (first.getDay() + 6) % 7 // 周一开头
  const cells = []
  for (let i = 0; i < lead; i++) cells.push(null)
  for (let d = 1; d <= days; d++) {
    const key = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ day: d, count: stats.value.calendar?.[key] || 0 })
  }
  return cells
})

function dotColor(n) {
  if (!n) return null
  return dotColors[Math.min(dotColors.length - 1, Math.floor((n - 1) / 3))]
}
function donutDash(pct) {
  const c = 2 * Math.PI * 45
  return `${c * Math.min(100, Math.max(0, pct)) / 100} ${c}`
}

onMounted(async () => {
  try {
    stats.value = await api.get('/stats')
  } catch (e) {
    error.value = e.message
  }
})
</script>

<template>
  <div>
    <p v-if="error" class="err">{{ error }}</p>

    <div v-if="stats" class="dash">
      <!-- 第一行：今日订单 + 运单状态 -->
      <div class="panel today-panel">
        <div class="panel-head"><h3>今日订单</h3><span class="hint">{{ now.getMonth() + 1 }}月{{ now.getDate() }}日</span></div>
        <div class="today-body">
          <div class="today-big">
            <div class="big-num">{{ stats.today_new }}</div>
            <div class="big-label">今日运单</div>
          </div>
          <div class="mini-cards">
            <div v-for="c in todayCards" :key="c.key" class="mini-card" :style="{ background: cardColors[c.key].bg }">
              <div>
                <div class="mini-num">{{ c.count }}</div>
                <div class="mini-label">{{ c.label }}</div>
              </div>
              <span class="mini-dot" :style="{ background: cardColors[c.key].dot }"></span>
            </div>
          </div>
        </div>
      </div>

      <div class="panel status-panel">
        <div class="panel-head"><h3>运单状态</h3></div>
        <div class="status-body">
          <div class="bars">
            <div v-for="b in statusBars" :key="b.key" class="bar-row">
              <span class="bar-label">{{ b.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: b.pct + '%', background: barColors[b.key] }"></div>
              </div>
              <span class="bar-count">{{ b.count }}</span>
            </div>
          </div>
          <div class="donut-box">
            <svg viewBox="0 0 110 110" class="donut">
              <circle cx="55" cy="55" r="45" fill="none" stroke="#eef1f6" stroke-width="10" />
              <circle cx="55" cy="55" r="45" fill="none" stroke="#6366f1" stroke-width="10"
                      stroke-linecap="round" :stroke-dasharray="donutDash(stats.completion_rate)"
                      transform="rotate(-90 55 55)" />
              <text x="55" y="52" text-anchor="middle" class="donut-num">{{ stats.completion_rate }}%</text>
              <text x="55" y="66" text-anchor="middle" class="donut-sub">签收完成率</text>
            </svg>
          </div>
        </div>
      </div>

      <!-- 第二行：网点情况 + 物流情况 + 本月业务日历 -->
      <div class="panel">
        <div class="panel-head"><h3>网点情况</h3></div>
        <div class="kv-row">
          <div class="kv"><span class="kv-num">{{ stats.branches }}</span><span class="kv-label">网点总数</span></div>
          <div class="kv"><span class="kv-num">{{ stats.branch_weight }}</span><span class="kv-label">运输总量(kg)</span></div>
        </div>
        <div class="rank-head">网点运单量排行</div>
        <div v-for="(b, i) in stats.branch_rank" :key="b.name" class="rank-row">
          <span class="rank-idx" :style="{ background: dotColors[i % 4] }">{{ i + 1 }}</span>
          <span class="rank-name">{{ b.name }}</span>
          <span class="rank-val">{{ b.orders }} 单 / {{ b.weight }}kg</span>
        </div>
        <div v-if="!stats.branch_rank.length" class="empty" style="padding: 12px">暂无数据</div>
      </div>

      <div class="panel">
        <div class="panel-head"><h3>物流情况</h3></div>
        <div class="kv-row">
          <div class="kv"><span class="kv-num">{{ stats.total_orders }}</span><span class="kv-label">总运单</span></div>
          <div class="kv"><span class="kv-num green">{{ stats.normal_rate }}%</span><span class="kv-label">正常率</span></div>
          <div class="kv"><span class="kv-num red">{{ stats.exception_rate }}%</span><span class="kv-label">异常率</span></div>
        </div>
        <div class="trend">
          <div v-for="t in stats.trend" :key="t.date" class="trend-col" :title="`${t.date}：${t.count} 单`">
            <div class="trend-bar" :style="{ height: Math.round(t.count / maxTrend * 56) + 'px' }"></div>
            <div class="trend-date">{{ t.date }}</div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head"><h3>本月业务日历</h3><span class="hint">{{ now.getFullYear() }}年{{ now.getMonth() + 1 }}月</span></div>
        <div class="cal-week">
          <span v-for="w in ['一', '二', '三', '四', '五', '六', '日']" :key="w">{{ w }}</span>
        </div>
        <div class="cal-grid">
          <div v-for="(cell, i) in calendarCells" :key="i" class="cal-cell">
            <template v-if="cell">
              <span class="cal-day">{{ cell.day }}</span>
              <span v-if="cell.count" class="cal-dot" :style="{ background: dotColor(cell.count) }" :title="`${cell.count} 单`"></span>
            </template>
          </div>
        </div>
      </div>

      <!-- 第三行：待办公告 + 运单总览 + 车辆排行 + 司机排行 -->
      <div class="panel">
        <div class="panel-head"><h3>待办 / 公告</h3></div>
        <div class="todo-row"><span class="todo-dot" style="background:#f59e0b"></span>待揽收运单 {{ stats.by_status.pending || 0 }} 单待处理</div>
        <div class="todo-row"><span class="todo-dot" style="background:#ef4444"></span>异常运单 {{ stats.by_status.exception || 0 }} 单需跟进</div>
        <div class="todo-row"><span class="todo-dot" style="background:#3b82f6"></span>系统正常运行，每月 1 日生成月报</div>
      </div>

      <div class="panel">
        <div class="panel-head"><h3>运单总览</h3></div>
        <div class="vehicle-donut-wrap">
          <svg viewBox="0 0 110 110" class="donut small">
            <circle cx="55" cy="55" r="45" fill="none" stroke="#eef1f6" stroke-width="10" />
            <circle cx="55" cy="55" r="45" fill="none" stroke="#22c55e" stroke-width="10"
                    stroke-linecap="round" :stroke-dasharray="donutDash(stats.vehicle_usage)"
                    transform="rotate(-90 55 55)" />
            <text x="55" y="52" text-anchor="middle" class="donut-num">{{ stats.vehicle_usage }}%</text>
            <text x="55" y="66" text-anchor="middle" class="donut-sub">车辆使用率</text>
          </svg>
          <div class="vehicle-legend">
            <div><i style="background:#22c55e"></i>空闲 {{ stats.vehicle_by_status.idle || 0 }}</div>
            <div><i style="background:#3b82f6"></i>在途 {{ stats.vehicle_by_status.transit || 0 }}</div>
            <div><i style="background:#f59e0b"></i>维修 {{ stats.vehicle_by_status.maintenance || 0 }}</div>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head"><h3>本月车辆接单排行</h3></div>
        <div v-for="(v, i) in stats.vehicle_rank" :key="v.plate" class="rank-row">
          <img :src="truckImage(v.model)" class="rank-img" />
          <span class="rank-idx" :style="{ background: dotColors[i % 4] }">{{ i + 1 }}</span>
          <span class="rank-name">{{ v.plate }}</span>
          <span class="rank-val">{{ v.orders }} 单</span>
        </div>
        <div v-if="!stats.vehicle_rank.length" class="empty" style="padding: 12px">暂无数据</div>
      </div>

      <div class="panel">
        <div class="panel-head"><h3>本月司机接单排行</h3></div>
        <div v-for="(d, i) in stats.driver_rank" :key="d.name" class="rank-row">
          <span class="rank-idx" :style="{ background: dotColors[i % 4] }">{{ i + 1 }}</span>
          <span class="rank-name">{{ d.name }}</span>
          <span class="rank-val">{{ d.orders }} 单</span>
        </div>
        <div v-if="!stats.driver_rank.length" class="empty" style="padding: 12px">暂无数据</div>
      </div>
    </div>

    <!-- 品牌宣传视频 -->
    <div class="promo-wrap">
      <div class="promo-head">
        <h3>品牌宣传</h3>
        <span class="hint">鼠标悬停播放</span>
      </div>
      <div class="promo-grid">
        <div v-for="p in promos" :key="p.title" class="promo-card" @mouseenter="playVideo" @mouseleave="stopVideo">
          <video :src="p.src" :poster="p.poster" muted loop playsinline preload="none"></video>
          <div class="promo-caption">
            <b>{{ p.title }}</b>
            <span>{{ p.desc }}</span>
          </div>
          <span class="promo-play">▶</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dash { display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; grid-column: span 3; }
.today-panel { grid-column: span 5; }
.status-panel { grid-column: span 7; }

/* 品牌宣传视频 */
.promo-wrap { margin-top: 18px; }
.promo-head { display: flex; justify-content: space-between; align-items: center; border-left: 3px solid var(--primary); padding-left: 8px; margin-bottom: 12px; }
.promo-head h3 { margin: 0; font-size: 14px; }
.promo-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.promo-card {
  position: relative; border-radius: 10px; overflow: hidden; cursor: pointer;
  aspect-ratio: 16 / 9; background: #0f172a;
}
.promo-card video { width: 100%; height: 100%; object-fit: cover; display: block; }
.promo-caption {
  position: absolute; left: 0; right: 0; bottom: 0; padding: 26px 14px 10px;
  background: linear-gradient(transparent, rgba(0, 0, 0, .72)); color: #fff;
  display: flex; flex-direction: column; gap: 2px; pointer-events: none;
}
.promo-caption b { font-size: 14px; }
.promo-caption span { font-size: 12px; opacity: .85; }
.promo-play {
  position: absolute; top: 10px; right: 10px; width: 30px; height: 30px; border-radius: 50%;
  background: rgba(0, 0, 0, .55); color: #fff; font-size: 11px;
  display: flex; align-items: center; justify-content: center; pointer-events: none;
}
.promo-card:hover .promo-play { opacity: 0; transition: opacity .2s; }

.panel-head { display: flex; justify-content: space-between; align-items: center; border-left: 3px solid var(--primary); padding-left: 8px; margin-bottom: 12px; }
.panel-head h3 { margin: 0; font-size: 14px; }
.hint { color: var(--muted); font-size: 12px; }

.today-body { display: flex; gap: 16px; align-items: stretch; }
.today-big { width: 96px; display: flex; flex-direction: column; justify-content: center; align-items: center; background: #f8fafc; border-radius: 8px; }
.big-num { font-size: 34px; font-weight: 700; }
.big-label { color: var(--muted); font-size: 12px; margin-top: 2px; }
.mini-cards { flex: 1; display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.mini-card { border-radius: 8px; padding: 10px 12px; display: flex; justify-content: space-between; align-items: center; }
.mini-num { font-size: 20px; font-weight: 700; }
.mini-label { font-size: 12px; color: var(--muted); }
.mini-dot { width: 26px; height: 26px; border-radius: 50%; opacity: .9; }

.status-body { display: flex; gap: 20px; align-items: center; }
.bars { flex: 1; }
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.bar-label { width: 52px; font-size: 13px; color: var(--muted); }
.bar-track { flex: 1; height: 10px; background: #eef1f6; border-radius: 5px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 5px; }
.bar-count { width: 34px; text-align: right; font-size: 13px; }
.donut-box { width: 150px; }
.donut { width: 100%; display: block; }
.donut-num { font-size: 16px; font-weight: 700; fill: var(--text); }
.donut-sub { font-size: 9px; fill: var(--muted); }

.kv-row { display: flex; gap: 10px; margin-bottom: 12px; }
.kv { flex: 1; background: #f8fafc; border-radius: 8px; text-align: center; padding: 10px 4px; }
.kv-num { display: block; font-size: 20px; font-weight: 700; }
.kv-num.green { color: var(--ok); }
.kv-num.red { color: var(--danger); }
.kv-label { font-size: 12px; color: var(--muted); }

.rank-head { font-size: 12px; color: var(--muted); margin-bottom: 8px; }
.rank-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px dashed var(--line); font-size: 13px; }
.rank-row:last-child { border-bottom: none; }
.rank-idx { width: 18px; height: 18px; border-radius: 50%; color: #fff; font-size: 11px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; }
.rank-img { width: 42px; height: 30px; object-fit: cover; border-radius: 5px; flex-shrink: 0; }
.rank-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-val { color: var(--muted); font-size: 12px; }

.trend { display: flex; align-items: flex-end; gap: 4px; height: 76px; }
.trend-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }
.trend-bar { width: 100%; max-width: 18px; background: linear-gradient(180deg, #34d399, #059669); border-radius: 3px 3px 0 0; min-height: 2px; }
.trend-date { font-size: 9px; color: var(--muted); transform: scale(.85); margin-top: 4px; white-space: nowrap; }

.cal-week, .cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.cal-week span { text-align: center; font-size: 11px; color: var(--muted); padding: 2px 0; }
.cal-cell { height: 34px; border-radius: 6px; background: #f8fafc; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; }
.cal-day { font-size: 11px; line-height: 1; }
.cal-dot { width: 6px; height: 6px; border-radius: 50%; }

.todo-row { display: flex; align-items: center; gap: 8px; font-size: 13px; padding: 6px 0; border-bottom: 1px dashed var(--line); }
.todo-row:last-child { border-bottom: none; }
.todo-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

.vehicle-donut-wrap { display: flex; align-items: center; gap: 12px; }
.vehicle-donut-wrap .donut { width: 110px; }
.vehicle-legend { font-size: 12px; color: var(--muted); }
.vehicle-legend i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }

@media (max-width: 1100px) {
  .panel, .today-panel, .status-panel { grid-column: span 6; }
}
@media (max-width: 700px) {
  .panel, .today-panel, .status-panel { grid-column: span 12; }
}
</style>
