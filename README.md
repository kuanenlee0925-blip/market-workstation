# Market Workstation — Part 1

A localhost Vue + FastAPI + SQLite workstation with Yahoo streaming, candlesticks and volume, recorded replay, higher timeframes and source transparency. The student's dark terminal design is retained. This update covers supplied prompts 01–09 (including 07A). Later trading/AI/voice prompts are reference only. No real orders are placed.

Repository: https://github.com/kuanenlee0925-blip/market-workstation (public).

## Structure

```text
backend/              FastAPI routes, Yahoo lifecycle, SQLite, candles and tests
  data/               Labeled synthetic CSV fixture
frontend/             Vue terminal dashboard, chart adapter and browser tests
scripts/              SmokeTest and bounded Yahoo diagnostic
docs/                 Design pipeline, verification and curated evidence
prompts/              Preserved supplied prompt files and sample data
handoffs/             Resume instructions and current project state
AGENTS.md             Standing project instructions
AI-USE.md             Tool/model disclosure
report.md             Canvas Part 1 report
```

## Environment and dependencies

Use the existing Python environment; do not create/recreate a virtual environment by default. This computer uses `.venv\Scripts\python.exe` (Python 3.14.7), Node 24.20.0 and npm. CI uses Python 3.12 and Node 22. Vite requires Node 20.19+ or 22.12+; a modern Chromium browser is needed for chart testing.

Backend dependencies are in `backend/requirements.txt`; `requirements-lock.txt` records the observed local environment. The frontend manifest and npm lockfile are in `frontend/`. The student approved adding exchange-calendars 4.x to the existing environment for sessions/holidays/DST/early closes. All other tools used here were already installed. For a different computer, select a suitable Python interpreter, inspect existing packages, and approve installation into that interpreter before running `python -m pip install -r backend/requirements.txt`, `npm.cmd ci` in frontend, or downloading a Playwright browser with `npx.cmd playwright install chromium`.

## Start and stop

From the project root on this configured Windows computer:

```powershell
cd frontend
npm.cmd run build
cd ..
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Stop with Ctrl+C in the server terminal. Localhost needs its backend running; restart it after a computer restart. SQLite automatically initializes/migrates `market.sqlite` in the working directory. No Yahoo login or API key is needed. `MARKET_DB` overrides the database path. Existing observations are preserved, and local `market.pre-prompts-*.sqlite` backups are ignored by Git.

For offline replay, set `$env:FEED_ENABLED='0'` before starting; set it back to `'1'` for normal Yahoo startup. Alternatively use Disconnect Yahoo / Reconnect Yahoo in the source panel. Disconnect closes Yahoo while leaving browser connections and replay usable. Never enable `MARKET_TEST_MODE` for ordinary use; it adds isolated-fixture ingestion routes solely for SmokeTest.

For development run `npm.cmd run dev` in frontend in a second terminal, then open http://127.0.0.1:5173. Vite proxies `/api` and `/ws` to the backend; `MARKET_API_URL` overrides the backend address for isolated tests. Direct and proxied `/api/health` must return identical JSON; the proxy fails when FastAPI stops and recovers after restart.

## Dashboard workflow

1. Choose AAPL, MSFT, SPY or BTC-USD from the watchlist or symbol selector. Stock candles use regular US equity sessions; out-of-session quotes are saved but excluded from these candles. BTC-USD uses UTC days.
2. Choose 1m, 5m, 15m, 1h or 1d. Larger bars derive from the same available one-minute records. The source, data age, feed status, provisional state and minute coverage stay visible.
3. Hover the chart or use Inspect candle to read its UTC timestamp, OHLC and volume. Unknown volume is shown as Unknown, not zero.
4. Enter an optional UTC range (start inclusive, end exclusive), then Apply range. Select Replay stored to reveal the recorded arrivals one per second. Its sequence, source time and receipt time are displayed. Replay is read-only and works with Yahoo disconnected. Repeat Replay stored to restart; Live feed returns to the current feed view. Clear range removes the filter.
5. CSV sample displays three labeled synthetic AAPL minutes from November 9, 2026. It writes no sample rows to the live database. In 5m view the sample is O100/H105/L99/C104/V3550 with coverage 3/5. It is not live evidence.

`GET /api/history` serves that six-field synthetic sample by default. Use `?source=recorded&symbol=AAPL&interval=5m&with_metadata=true` for recorded history and separate completion/coverage metadata. See [design-pipeline.md](docs/design-pipeline.md) for the schema, identity assumptions, session rules and replay boundaries.

## Checks

```powershell
.\.venv\Scripts\python -m pytest backend -q
cd frontend
npm.cmd run build
cd ..
.\.venv\Scripts\python scripts/smoke_test.py
```

SmokeTest starts backend and Vue on unused ports, uses an isolated temporary database with labeled deterministic events, opens real Chromium, and tests CSV, timeframes, candle inspection, live/replay transport, repeat replay without database changes, validation, source controls, mobile layout, frontend-proxy failure/recovery and persisted rows after restart. It exits nonzero on failure and cleans up its owned services/database. It does not edit source or install packages. Run it twice for clean-account reproducibility. CI runs the same command without Yahoo or provider credentials.

Real Yahoo is checked separately:

```powershell
.\.venv\Scripts\python scripts/check_yahoo.py --symbol BTC-USD --timeout 15
cd frontend
$env:LIVE_TEST='1'
npx.cmd playwright test --grep 'optional Yahoo'
```

The browser live check needs the ordinary application running on port 8000. It requires a new receipt after the test starts, compares the chart price with saved data, deliberately disconnects Yahoo while the browser remains connected, replays, and reconnects. A quiet/unavailable source can make this check fail; no synthetic fallback is substituted.

## Submission and limitations

Upload only [report.md](report.md) to Canvas. It links the public repository, application commit and [updated 58-second video](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/docs/demo-2026-11-10.mp4). The November 10 video shows the current UI, live data, timeframe/inspection controls and source disconnect/unavailability. It does not show range selection, stored replay or successful reconnect recovery; the report identifies those gaps. The original baseline demo.mp4 is retained separately. Do not upload code or ZIPs to Canvas.

See [current verification](docs/verification.md), [evidence](docs/evidence.md), [design](docs/design-pipeline.md), and [AI disclosure](AI-USE.md). Quotes are sampled; volume/coverage is not exchange-certified. Recording remains unbounded and aggregation is intended for a small local demonstration. The calendar covers 2000–2035; unsupported/out-of-session equity observations are kept in SQLite but do not form regular-session candles.

## References

- [yfinance streaming](https://ranaroussi.github.io/yfinance/reference/yfinance.websocket.html) and [usage terms](https://pypi.org/project/yfinance/): independent of Yahoo; research/educational and personal-use data limitations apply.
- [exchange-calendars](https://github.com/gerrymanoim/exchange_calendars): regular sessions, holidays, early closes and DST.
- [Lightweight Charts](https://tradingview.github.io/lightweight-charts/docs), by TradingView, Inc. https://www.tradingview.com/. Chart logo and attribution link are retained.
