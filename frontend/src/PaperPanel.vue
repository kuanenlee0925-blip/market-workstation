<script setup>

import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({ symbol: String, interval: String, mode: String, testMode: Boolean })

const selected = ref(''), accounts = ref([]), account = ref(null), error = ref(''), busy = ref(false)

const initial = ref(1000), short = ref(2), long = ref(3), size = ref(4), quantity = ref(4)

const source = ref('reference'), start = ref(''), end = ref(''), showHistory = ref(true)

let timer, lastRequest = null

const usd = n => n == null ? 'Unavailable' : Number(n).toLocaleString('en-US', { style:'currency', currency:'USD' })

const utc = n => n == null ? '—' : new Date(n*1000).toISOString().replace('T',' ').replace('.000Z',' UTC')

const equityPoints = computed(() => {

  const rows = account.value?.pnl || []

  if (!rows.length) return ''

  const values = rows.map(row => row.equity), low = Math.min(...values), spread = Math.max(...values)-low || 1

  return values.map((value, i) => `${i/Math.max(1, values.length-1)*600},${60-(value-low)/spread*50}`).join(' ')

})

async function api(path, body) {

  const response = await fetch(path, body === undefined ? {} : { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) })

  const result = await response.json()

  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Check the positive whole-number settings and try again')

  return result

}

async function list() {

  const result = await api('/api/paper/accounts'); accounts.value = result.accounts

  if (result.health.error) error.value = `Paper account processing needs attention (${result.health.error})`

}

async function load() {

  if (!selected.value) return

  const id = selected.value, result = await api(`/api/paper/accounts/${id}`)

  if (id === selected.value) account.value = result

}

async function action(work) {

  if (busy.value) return

  busy.value = true; error.value = ''

  try { await work() } catch (failure) { error.value = failure.message } finally { busy.value = false }

}

const config = () => ({ symbol:props.symbol, interval:props.interval || '1m', initial:Number(initial.value), short:Number(short.value), long:Number(long.value), size:Number(size.value) })

async function create() { await action(async () => { account.value = await api('/api/paper/accounts', config()); selected.value = account.value.id; await list() }) }

async function run() { await action(async () => { account.value = await api('/api/backtests', { ...config(), source:source.value, start:start.value ? start.value+'Z' : null, end:end.value ? end.value+'Z' : null }); selected.value = account.value.id; await list() }) }

async function order(side, retry=false) {

  await action(async () => {

    if (!retry) lastRequest = { id:account.value.id, body:{ request_id:crypto.randomUUID(), side, quantity:side === 'close' ? null : Number(quantity.value) } }

    if (!lastRequest || lastRequest.id !== selected.value) throw new Error('No request to retry for this account')

    account.value = await api(`/api/paper/accounts/${selected.value}/orders`, lastRequest.body)

  })

}

async function strategy() { await action(async () => { account.value = await api(`/api/paper/accounts/${selected.value}/strategy`, {enabled:!account.value.summary.strategy}) }) }

onMounted(async () => {

  await action(list)

  timer = setInterval(() => { if (!busy.value && account.value?.config.source === 'live') load().catch(failure => error.value = failure.message) }, 1500)

})

onUnmounted(() => clearInterval(timer))

</script>



<template>

  <section class="paper-panel" aria-label="Simulation and backtesting">

    <div class="section-heading"><h2>Simulated trading & backtesting</h2><span class="tiny-badge">No real orders · USD</span></div>

    <p class="paper-note">SMA up → buy when flat. SMA down → close. Signals use completed candles; fills wait for the next eligible observation after the signal. Zero fees and slippage.</p>

    <div class="paper-controls">

      <label>Starting cash<input aria-label="Starting paper cash" type="number" min="1" v-model.number="initial" /></label>

      <label>Short SMA<input aria-label="Strategy short window" type="number" min="1" v-model.number="short" /></label>

      <label>Long SMA<input aria-label="Strategy long window" type="number" min="2" v-model.number="long" /></label>

      <label>Order size<input aria-label="Strategy order size" type="number" min="1" v-model.number="size" /></label>

      <button :disabled="busy" @click="create">Create paper account</button>

    </div>

    <p class="micro">New account: {{ symbol }} · {{ interval }} · Yahoo arrivals after creation. Previously recorded prices cannot fill a new manual order.</p>

    <details class="backtest-controls" open><summary>Historical backtest</summary>

      <div class="paper-controls">

        <label>Dataset<select aria-label="Backtest dataset" v-model="source"><option value="reference">Synthetic SMA reference · not live</option><option value="recorded">Recorded Yahoo arrivals · historical</option></select></label>

        <label>Receipt time from · UTC<input aria-label="Backtest start UTC" type="datetime-local" v-model="start" /></label>

        <label>Receipt time to · UTC (exclusive)<input aria-label="Backtest end UTC" type="datetime-local" v-model="end" /></label>

        <button :disabled="busy" @click="run">{{ busy ? 'Working…' : 'Run backtest' }}</button>

      </div>

      <p class="micro">Uses the cash, windows and size above. Recorded data uses {{ symbol }} / {{ interval }}; the synthetic reference uses AAPL. Each run saves a separate account and frozen inputs. Limit 3,000 observations.</p>

    </details>

    <p v-if="error" role="alert" class="paper-error">{{ error }}</p>

    <label class="paper-saved">Saved account / run<select aria-label="Saved paper account" v-model="selected" @change="action(load)"><option value="">Select a saved account</option><option v-for="item in accounts" :key="item.id" :value="item.id">{{ item.config.symbol }} · {{ item.config.source }} · SMA {{ item.config.short }}/{{ item.config.long }} · {{ item.id.slice(0,8) }}</option></select></label>

    <template v-if="account">

      <div class="paper-context"><b>{{ account.config.symbol }} · {{ account.config.interval }} · SMA {{ account.config.short }}/{{ account.config.long }}</b><span>{{ account.config.source === 'live' ? (testMode ? 'Paper account - synthetic test arrivals' : 'Paper account - live arrivals only') : account.config.source }}</span><small v-if="account.inputs">{{ account.inputs.observations }} observations · Received {{ utc(account.inputs.first_receipt) }} to {{ utc(account.inputs.last_receipt) }} · Input SHA-256 {{ account.inputs.sha256.slice(0,16) }}…</small><small>Account {{ account.id }} · Initial {{ usd(account.config.initial) }}</small></div>

      <div class="paper-metrics" data-testid="paper-summary">

        <div><span>Cash</span><b data-testid="paper-cash">{{ usd(account.summary.cash) }}</b></div>

        <div><span>Shares / average cost</span><b>{{ account.summary.quantity }} / {{ usd(account.summary.average_cost) }}</b></div>

        <div><span>Realized P&L</span><b>{{ usd(account.summary.realized) }}</b></div>

        <div><span>Unrealized P&L</span><b>{{ usd(account.summary.unrealized) }}</b></div>

        <div><span>Equity / return</span><b>{{ usd(account.summary.equity) }} / {{ account.summary.return_percent?.toFixed(2) ?? '—' }}%</b></div>

        <div><span>Sampled max drawdown</span><b>{{ account.summary.max_drawdown_percent.toFixed(2) }}%</b></div>

      </div>

      <p class="paper-note">Valuation: {{ usd(account.summary.price) }} · {{ account.summary.price_source || 'No usable price yet' }} · Source {{ utc(account.summary.price_source_time) }}  |  Recorded {{ utc(account.summary.price_time) }}. {{ account.fills.length }} fills. Weighted-average cost; an open position is not force-closed at the end.</p>

      <div v-if="account.config.source === 'live'" class="paper-controls">

        <button :disabled="busy" @click="strategy">{{ account.summary.strategy ? 'Pause SMA strategy' : 'Enable SMA strategy' }}</button>

        <label>Shares<input aria-label="Manual paper quantity" type="number" min="1" step="1" v-model.number="quantity" /></label>

        <button :disabled="busy || mode !== 'live'" @click="order('buy')">Buy paper</button><button :disabled="busy || mode !== 'live'" @click="order('sell')">Sell paper</button><button :disabled="busy || mode !== 'live'" @click="order('close')">Close paper</button><button :disabled="busy || mode !== 'live'" @click="order(null,true)">Retry last request</button>

        <p v-if="mode !== 'live'" class="micro">Switch the chart to Live feed for manual orders. An enabled SMA strategy continues processing new Yahoo arrivals independently of chart replay.</p>

      </div>

      <div v-if="account.pnl.length" class="equity-history"><span>Equity history · each recorded valuation</span><svg viewBox="0 0 600 70" role="img" aria-label="Simulated equity history" preserveAspectRatio="none"><polyline :points="equityPoints" /></svg></div>

      <button class="paper-history-toggle" @click="showHistory=!showHistory">{{ showHistory ? 'Hide' : 'Show' }} account history</button>

      <div v-if="showHistory" class="paper-history">

        <details open><summary>Orders ({{ account.orders.length }})</summary><div class="paper-table"><table aria-label="Paper order history"><thead><tr><th>Order / origin</th><th>Submitted UTC</th><th>Side / shares</th><th>Status / reason</th></tr></thead><tbody><tr v-for="o in account.orders" :key="o.id"><td :title="o.id">{{ o.id.slice(0,8) }} · {{ o.origin }}</td><td>{{ utc(o.submitted) }}</td><td>{{ o.side }} {{ o.quantity }}</td><td>{{ o.status }}{{ o.reason ? ' · '+o.reason : '' }}</td></tr></tbody></table></div></details>

        <details open><summary>Fills ({{ account.fills.length }})</summary><div class="paper-table"><table aria-label="Paper fill history"><thead><tr><th>Order</th><th>Side / shares</th><th>Price</th><th>Observation / source UTC</th><th>Execution UTC</th></tr></thead><tbody><tr v-for="f in account.fills" :key="f.id"><td>{{ f.order_id.slice(0,8) }}</td><td>{{ f.side }} {{ f.quantity }}</td><td>{{ usd(f.price) }}</td><td>#{{ f.observation_sequence }} · {{ utc(f.source_time) }}</td><td>{{ utc(f.executed) }}</td></tr></tbody></table></div></details>

        <details open><summary>P&L history ({{ account.pnl.length }})</summary><div class="paper-table"><table aria-label="Paper profit and loss history"><thead><tr><th>Time / event / price</th><th>Cash / shares</th><th>Realized</th><th>Unrealized</th><th>Total</th><th>Equity</th></tr></thead><tbody><tr v-for="p in account.pnl" :key="p.event_key"><td :title="p.source">{{ utc(p.timestamp) }} · {{ p.event }} · {{ usd(p.price) }}</td><td>{{ usd(p.cash) }} / {{ p.quantity }}</td><td>{{ usd(p.realized) }}</td><td>{{ usd(p.unrealized) }}</td><td>{{ usd(p.total) }}</td><td>{{ usd(p.equity) }}</td></tr></tbody></table></div></details>

        <details><summary>Completed-candle signals ({{ account.signals.length }})</summary><div class="paper-table"><table aria-label="Strategy signal history"><thead><tr><th>Candle UTC</th><th>Short</th><th>Long</th><th>Crossover</th><th>Available at UTC</th></tr></thead><tbody><tr v-for="s in account.signals" :key="s.timestamp"><td>{{ s.timestamp }}</td><td>{{ s.short ?? 'Warm-up' }}</td><td>{{ s.long ?? 'Warm-up' }}</td><td>{{ s.crossover || '—' }}</td><td>{{ utc(s.available_at) }} · #{{ s.observation_sequence }}</td></tr></tbody></table></div></details>

      </div>

      <p class="paper-note">Historical results describe this sample and execution model. Gaps, delayed quotes, zero costs, survivorship bias, and parameter tuning can distort results. They do not establish future profitability. <a href="https://github.com/kuanenlee0925-blip/market-workstation/blob/main/docs/part2-design.md" target="_blank" rel="noreferrer">Assumptions ↗</a></p>

    </template>

  </section>

</template>

