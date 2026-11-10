<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { createChart, CandlestickSeries, HistogramSeries } from 'lightweight-charts'
const instruments = [
  { symbol: 'AAPL', name: 'Apple Inc.', icon: 'A', color: '#d8dde6', type: 'NASDAQ · EQUITY' },
  { symbol: 'MSFT', name: 'Microsoft Corporation', icon: '⊞', color: '#70adfa', type: 'NASDAQ · EQUITY' },
  { symbol: 'SPY', name: 'SPDR S&P 500 ETF', icon: 'S', color: '#bf9afa', type: 'NYSE ARCA · ETF' },
  { symbol: 'BTC-USD', name: 'Bitcoin / US Dollar', icon: '₿', color: '#f4a440', type: 'CRYPTO · USD' },
]
const symbol = ref('AAPL'), state = ref({ bars: [], feed: {} }), connection = ref('connecting')
const host = ref(), now = ref(Date.now()/1000), search = ref(''), quotes = ref({})
const interval = ref('1m'), rangeStart = ref(''), rangeEnd = ref(''), error = ref(''), hoverTime = ref(null)
let chart, candles, volume, socket, retry, timer, disposed = false
const watchSockets = new Set(), watchRetries = new Set()
const latest = computed(() => state.value.bars.at(-1))
const inspected = computed(() => state.value.bars.find(b => b.time === hoverTime.value) || latest.value)
const instrument = computed(() => instruments.find(i => i.symbol === symbol.value))
const filtered = computed(() => instruments.filter(i => `${i.symbol} ${i.name}`.toLowerCase().includes(search.value.toLowerCase())))
const age = computed(() => state.value.last_source_time ? `${Math.max(0, Math.floor(now.value-state.value.last_source_time))}s` : '—')
const stats = computed(() => {
  const bars = state.value.bars
  if (!bars.length) return { high: null, low: null, open: null, volume: null, change: null, position: 0 }
  const high = Math.max(...bars.map(b => b.high)), low = Math.min(...bars.map(b => b.low))
  const open = bars[0].open, close = bars.at(-1).close
  return { high, low, open, volume: bars.some(b => b.volume == null) ? null : bars.reduce((sum,b) => sum+b.volume, 0), change: (close/open-1)*100, position: high === low ? 50 : (close-low)/(high-low)*100 }
})
const recent = computed(() => [...state.value.bars].reverse().slice(0, 3))
const price = n => n == null ? '—' : n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const compact = n => n == null ? '—' : Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(n)
const volumeText = n => n == null ? 'Unknown' : compact(n)
const candleTime = n => n ? new Date(n*1000).toISOString().replace('T', ' ').replace('.000Z', ' UTC') : '—'
const percent = n => n == null ? '—' : `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
const clock = n => n ? new Date(n*1000).toLocaleTimeString('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'
const direction = n => n == null ? '' : n >= 0 ? 'up' : 'down'
function change(data) { const bars = data?.bars; return bars?.length ? (bars.at(-1).close/bars[0].open-1)*100 : null }
function spark(data) {
  const values = data?.bars?.slice(-30).map(b => b.close) || []
  if (values.length < 2) return ''
  const min = Math.min(...values), spread = Math.max(...values)-min || 1
  return values.map((v,i) => `${i/(values.length-1)*100},${30-(v-min)/spread*25}`).join(' ')
}
function url(s) { return `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/${s}` }
function merge(previous, packet) {
  const records = packet.type === 'snapshot' ? new Map() : new Map((previous?.bars || []).map(b => [b.timestamp, b]))
  for (const key of packet.removed || []) records.delete(key)
  for (const b of packet.bars || packet.updates || []) records.set(b.timestamp, b)
  const metadata = packet.metadata || previous?.metadata || {}
  const bars = [...records.values()].sort((a,b) => a.timestamp.localeCompare(b.timestamp)).map(b => ({ ...b, time: Date.parse(b.timestamp)/1000, ...metadata[b.timestamp] }))
  return { ...previous, ...packet, bars }
}
function paint(packet) {
  const point = b => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close })
  const histogram = b => b.volume == null ? { time: b.time } : { time: b.time, value: b.volume, color: b.close >= b.open ? '#42bcb54d' : '#ed81554d' }
  const changed = packet.updates || []
  const lastTime = state.value.bars.at(-1)?.time
  if (packet.type === 'snapshot' || packet.removed?.length || changed.some(b => Date.parse(b.timestamp)/1000 < lastTime)) {
    candles.setData(state.value.bars.map(point)); volume.setData(state.value.bars.map(histogram))
  } else {
    for (const b of changed) { const adapted = { ...b, time: Date.parse(b.timestamp)/1000 }; candles.update(point(adapted)); volume.update(histogram(adapted)) }
  }
}
function watchMarket(s) {
  if (disposed) return
  const ws = new WebSocket(url(s)); watchSockets.add(ws)
  ws.onmessage = event => { const packet = JSON.parse(event.data); if (packet.type !== 'error') quotes.value[s] = merge(quotes.value[s], packet) }
  ws.onclose = () => {
    watchSockets.delete(ws)
    if (disposed) return
    const id = setTimeout(() => { watchRetries.delete(id); watchMarket(s) }, 3000)
    watchRetries.add(id)
  }
}
function connect(nextMode = 'live') {
  clearTimeout(retry)
  if (socket) { socket.onclose = null; socket.close() }
  state.value = { bars: [], feed: {} }; connection.value = 'connecting'; hoverTime.value = null; error.value = ''
  candles.setData([]); volume.setData([])
  const current = new WebSocket(url(symbol.value)); socket = current
  let fitted = false
  current.onopen = () => { if (socket === current) { connection.value = 'connected'; if (nextMode !== 'live' || interval.value !== '1m' || rangeStart.value || rangeEnd.value) mode(nextMode) } }
  current.onmessage = event => {
    if (socket !== current) return
    const packet = JSON.parse(event.data)
    if (packet.type === 'error') { error.value = packet.message; return }
    state.value = merge(state.value, packet)
    paint(packet)
    if (!fitted && state.value.bars.length) { chart.timeScale().fitContent(); fitted = true }
  }
  current.onclose = () => { connection.value = 'disconnected'; if (!disposed) retry = setTimeout(() => connect(nextMode), 3000) }
  current.onerror = () => { if (socket === current) connection.value = 'unavailable' }
}
function select(s) { if (s !== symbol.value) { symbol.value = s; connect() } }
function mode(value) {
  error.value = ''
  if (rangeStart.value && rangeEnd.value && rangeStart.value >= rangeEnd.value) { error.value = 'Range end must be after its start'; return }
  if (value === 'sample' && symbol.value !== 'AAPL') { symbol.value = 'AAPL'; connect('sample'); return }
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ mode: value, interval: interval.value, start: rangeStart.value ? `${rangeStart.value}Z` : null, end: rangeEnd.value ? `${rangeEnd.value}Z` : null }))
}
async function toggleFeed() {
  try {
    const response = await fetch('/api/feed', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: !state.value.feed_enabled }) })
    if (!response.ok) throw new Error('Feed control unavailable')
    const result = await response.json(); state.value.feed = result.feed; state.value.feed_enabled = result.enabled
  } catch (failure) { error.value = failure.message }
}
onMounted(() => {
  chart = createChart(host.value, { autoSize: true, height: 440, layout: { background: { color: '#080d14' }, textColor: '#69788e', fontSize: 10, attributionLogo: true }, grid: { vertLines: { visible: false }, horzLines: { color: '#151d29' } }, timeScale: { timeVisible: true, secondsVisible: false, borderColor: '#202937', rightOffset: 4 }, rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.12, bottom: 0.08 } } })
  candles = chart.addSeries(CandlestickSeries, { upColor: '#4fc5bd', downColor: '#f18a5b', borderVisible: false, wickUpColor: '#4fc5bd', wickDownColor: '#f18a5b' })
  volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: 'volume' }, 1)
  chart.panes()[1].setHeight(75)
  chart.subscribeCrosshairMove(event => hoverTime.value = typeof event.time === 'number' ? event.time : null)
  connect(); instruments.forEach(i => watchMarket(i.symbol))
  timer = setInterval(() => now.value = Date.now()/1000, 1000)
})
onUnmounted(() => {
  disposed = true; clearInterval(timer); clearTimeout(retry); watchRetries.forEach(clearTimeout)
  socket?.close(); watchSockets.forEach(ws => ws.close()); chart?.remove()
})
</script>

<template>
  <div class="terminal">
    <header class="topbar">
      <a href="#workspace" class="brand"><span class="brand-icon">◈</span> Market<span>desk</span></a>
      <nav aria-label="Main navigation"><a href="#workspace" class="active">Workstation</a><a href="#activity">Market activity</a><a href="#source">Connection</a></nav>
      <div class="top-actions"><label class="search"><span>⌕</span><input v-model="search" aria-label="Search markets" placeholder="Search markets" /></label><span class="simulation">Simulation only</span><span class="avatar">MK</span></div>
    </header>
    <div class="ticker" aria-label="Live market ticker">
      <button v-for="i in instruments" :key="i.symbol" @click="select(i.symbol)"><span class="ticker-dot" :style="{ background: i.color }"></span><b>{{ i.symbol }}</b><span>{{ price(quotes[i.symbol]?.bars?.at(-1)?.close) }}</span><span :class="direction(change(quotes[i.symbol]))">{{ percent(change(quotes[i.symbol])) }}</span></button>
      <span class="ticker-label">CHANGE SINCE FIRST RECORDED BAR</span>
    </div>
    <div id="workspace" class="desk-grid">
      <aside class="watchlist">
        <div class="section-heading"><h2>Watchlist</h2><span class="counter">04</span></div>
        <div class="watch-labels"><span>Instrument</span><span>Last / change</span></div>
        <button v-for="i in filtered" :key="i.symbol" class="watch-row" :class="{ selected: symbol === i.symbol }" @click="select(i.symbol)">
          <span class="coin" :style="{ color: i.color, background: `${i.color}15` }">{{ i.icon }}</span>
          <span class="watch-name"><b>{{ i.symbol }}</b><small>{{ i.name }}</small></span>
          <span class="watch-value"><b>{{ price(quotes[i.symbol]?.bars?.at(-1)?.close) }}</b><small :class="direction(change(quotes[i.symbol]))">{{ percent(change(quotes[i.symbol])) }}</small></span>
        </button>
        <p v-if="!filtered.length" class="watch-empty">No matching markets.</p>
        <div class="watch-bottom"><span class="live-dot"></span> YAHOO FINANCE<span class="watch-caption">Live watchlist · USD<br>Changes cover recorded data, not a trading day.</span></div>
      </aside>
      <main class="center">
        <section class="chart-panel" aria-label="Market chart">
          <div class="instrument-heading"><span class="coin large" :style="{ color: instrument.color, background: `${instrument.color}15` }">{{ instrument.icon }}</span><h1>{{ instrument.name }}</h1><span class="exchange">{{ instrument.type }}</span><span class="currency">USD</span></div>
          <div class="quote"><strong>{{ price(latest?.close) }}</strong><span class="quote-change" :class="direction(stats.change)">{{ percent(stats.change) }} <small>recorded period</small></span><span class="quote-symbol">{{ symbol }}</span></div>
          <div class="chart-toolbar"><div class="modes"><button :class="{ selected: state.mode !== 'replay' }" @click="mode('live')">Live feed</button><button :class="{ selected: state.mode === 'replay' }" @click="mode('replay')">Replay stored</button></div><span class="toolbar-divider"></span><select aria-label="Chart timeframe" v-model="interval" @change="mode(state.mode || 'live')"><option v-for="frame in ['1m','5m','15m','1h','1d']" :key="frame">{{ frame }}</option></select><span class="chart-style">Candles + volume</span><button class="fit-button" @click="chart.timeScale().fitContent()">↔ Fit chart</button><select aria-label="Market symbol" v-model="symbol" @change="connect()"><option v-for="i in instruments" :key="i.symbol">{{ i.symbol }}</option></select></div>
          <div class="ohlc" aria-label="Candle details"><span>{{ candleTime(inspected?.time) }}</span><span>O <b>{{ price(inspected?.open) }}</b></span><span>H <b>{{ price(inspected?.high) }}</b></span><span>L <b>{{ price(inspected?.low) }}</b></span><span data-testid="inspected-close">C <b>{{ price(inspected?.close) }}</b></span><span data-testid="inspected-volume">V <b>{{ volumeText(inspected?.volume) }}</b></span><span v-if="inspected" class="dim">Coverage {{ inspected.observed_minutes }}/{{ inspected.expected_minutes }} minutes</span><span class="bar-status">{{ latest ? (latest.complete ? '● Complete' : '◌ Provisional candle') : 'Awaiting data' }}</span></div>
          <div class="selection-controls"><label>From · UTC<input type="datetime-local" aria-label="Replay range start UTC" v-model="rangeStart" /></label><label>To · UTC (exclusive)<input type="datetime-local" aria-label="Replay range end UTC" v-model="rangeEnd" /></label><button @click="mode(state.mode || 'live')">Apply range</button><button @click="rangeStart=''; rangeEnd=''; mode(state.mode || 'live')">Clear range</button><button @click="mode('sample')">CSV sample</button><label>Inspect candle<select aria-label="Inspect candle" v-model="hoverTime"><option :value="null">Latest candle</option><option v-for="b in state.bars" :key="b.timestamp" :value="b.time">{{ b.timestamp }}</option></select></label></div><p v-if="error" role="alert" class="view-warning">{{ error }}</p><p v-if="state.mode === 'sample'" class="view-warning">Synthetic CSV sample · November 9, 2026 · not live market data</p><p v-if="state.replay_point" class="replay-clock">REPLAY OBSERVATION #{{ state.replay_point.sequence }} · Source {{ state.replay_point.source_time }} · Received {{ state.replay_point.received_time }}</p><div class="chart-wrap"><div ref="host" class="chart"></div><div v-if="!state.bars.length" class="empty"><span class="empty-icon">⌁</span><strong>{{ state.mode === 'replay' ? 'No recorded observations in this range' : 'Waiting for market observations' }}</strong><span>Live quotes are saved automatically as they arrive.</span><span>Try BTC-USD when the stock market is closed.</span></div></div>
          <div class="chart-foot"><span><span class="live-dot" :class="{ offline: connection !== 'connected' }"></span>{{ state.mode === 'sample' ? 'Synthetic CSV sample' : state.mode === 'replay' ? 'Recorded replay' : 'Live' }} <span class="dim">/ {{ interval }} BARS</span></span><span>Source age <b>{{ age }}</b> <span class="separator">|</span> UTC {{ clock(now) }}</span></div>
        </section>
        <section id="activity" class="activity-section"><div class="section-heading"><h2>Market activity</h2><span class="dim">{{ symbol }} · RECORDED {{ interval }} BARS</span></div><div class="activity-cards"><article v-for="bar in recent" :key="bar.time" class="activity-card"><div class="card-heading"><span class="activity-icon" :class="bar.close >= bar.open ? 'up' : 'down'">{{ bar.close >= bar.open ? '↗' : '↘' }}</span><b>{{ clock(bar.time).slice(0,5) }} UTC</b><span class="tiny-badge">{{ bar.complete ? 'Complete' : 'Forming' }}</span></div><h3>{{ bar.close >= bar.open ? 'Close at or above open' : 'Price moved lower' }}</h3><p>Observed range {{ price(bar.low) }}–{{ price(bar.high) }}. Close {{ price(bar.close) }}.</p><div class="card-footer"><span>Volume Δ {{ volumeText(bar.volume) }}</span><span :class="bar.close >= bar.open ? 'up' : 'down'">{{ percent((bar.close/bar.open-1)*100) }}</span></div></article><div v-if="!recent.length" class="activity-placeholder">Recorded candle summaries will appear when observations arrive.</div></div></section>
        <div class="desk-note"><span>◈</span><p><b>Your market, in context.</b> Candles summarize received quotes. Volume is an observed cumulative delta; gaps can affect coverage.</p><a href="#source">View source details ↗</a></div>
      </main>
      <aside class="details">
        <section class="detail-section"><div class="section-heading"><h2>Recorded performance</h2><span class="dim">↗</span></div><div class="metric-cards"><div class="metric-card"><span>First open</span><strong>{{ price(stats.open) }}</strong><svg viewBox="0 0 100 36" aria-hidden="true"><polyline :points="spark(state)" /></svg></div><div class="metric-card"><span>Latest close</span><strong>{{ price(latest?.close) }}</strong><span :class="direction(stats.change)" class="metric-change">{{ percent(stats.change) }}</span></div></div><p class="micro">Based on this view’s recorded period.</p></section>
        <section class="detail-section"><div class="section-heading"><h2>Price range</h2><span class="tiny-badge">Observed</span></div><div class="range-price"><strong>{{ price(stats.low) }}</strong><strong>{{ price(stats.high) }}</strong></div><div class="range-track"><span v-if="latest" :style="{ left: `${stats.position}%` }"></span></div><div class="range-labels"><span>Recorded low</span><span>Recorded high</span></div><dl class="market-stats"><div><dt>Candle bars</dt><dd>{{ state.bars.length }}</dd></div><div><dt>Observed volume Δ</dt><dd>{{ volumeText(stats.volume) }}</dd></div><div><dt>Stored observations</dt><dd>{{ compact(state.count || 0) }}</dd></div></dl></section>
        <section id="source" class="detail-section"><div class="section-heading"><h2>Source transparency</h2><span class="status" :class="state.feed.status">● {{ state.feed.status || 'connecting' }}</span></div><dl><div><dt>Provider</dt><dd>{{ state.mode === 'sample' ? 'Synthetic CSV sample' : 'Yahoo Finance' }}</dd></div><div><dt>Browser socket</dt><dd>{{ connection }}</dd></div><div><dt>Source data age</dt><dd :class="{ down: Number.parseInt(age) > 60 }">{{ age }}</dd></div><div><dt>Source time · UTC</dt><dd>{{ clock(state.last_source_time) }}</dd></div><div><dt>Receipt time · UTC</dt><dd>{{ clock(state.last_received_time) }}</dd></div></dl><p class="source-note">{{ state.feed.detail || 'Connecting to the local backend…' }}</p><p v-if="state.replay_finished" class="source-note">Replay complete. Select Live feed to resume.</p><p v-if="Number.parseInt(age) > 60" class="source-note warning">{{ state.mode === 'replay' ? 'Historical replay: age is measured from the recorded source time.' : 'Quotes are over one minute old. The source may be quiet or delayed.' }}</p></section>
        <section class="session-panel"><button class="feed-toggle" @click="toggleFeed">{{ state.feed_enabled ? 'Disconnect Yahoo' : 'Reconnect Yahoo' }}</button><span class="session-icon">◷</span><div><b>{{ state.mode === 'sample' ? 'Synthetic sample' : 'Local session' }}</b><p>{{ state.feed_enabled ? 'Recording Yahoo to SQLite' : 'Yahoo disconnected; replay available' }}<br>All trading remains simulated.</p></div></section>
      </aside>
    </div>
    <footer><span><span class="live-dot" :class="{ offline: connection !== 'connected' }"></span> LOCAL WORKSTATION <span class="separator">/</span> <span class="dim">{{ state.mode === 'replay' ? 'REPLAY' : 'LIVE VIEW' }}</span></span><a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">Charts by TradingView Lightweight Charts™ ↗</a><span class="dim">SIMULATED ENVIRONMENT</span></footer>
  </div>
</template>
