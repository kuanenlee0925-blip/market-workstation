# Market Workstation

Local Vue + FastAPI + SQLite dashboard for Assignment 4.1. All trading remains simulated; this stage does not place orders or implement strategies or AI.

## Run on Windows

Requires Python 3.11+ and Node 20.19+ (or 22.12+).

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
cd frontend
npm.cmd ci
npm.cmd run build
cd ..
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. SQLite initializes automatically as `market.sqlite` in the working directory. No API credentials are required. `MARKET_DB` can override the database path. For frontend development run `npm.cmd run dev` inside `frontend` in a second terminal; Vite proxies API and WebSocket requests to port 8000.

Select AAPL, MSFT, SPY, or BTC-USD. Stock quotes may not arrive outside market hours; BTC-USD is another instrument to try, not a guarantee of feed availability. A connected socket is not evidence of current prices. Watch source age and feed status. No synthetic quotes are inserted. After observations arrive, select **Replay stored** to replay one recorded arrival per second; **Live feed** returns to the live view. Selecting Replay again restarts it.

## Verification

```powershell
.\.venv\Scripts\python -m pytest backend -q
cd frontend
npm.cmd run build
npx.cmd playwright install chromium
npx.cmd playwright test
```

Browser checks expect the built application running on port 8000. The default test mocks an unavailable source explicitly. To also test actual Yahoo data, set `$env:LIVE_TEST='1'` before running Playwright; this check can fail if the provider is unavailable.

Repository: https://github.com/kuanenlee0925-blip/market-workstation (public; no invitation required).

See [design](docs/design.md), [evidence](docs/evidence.md), [AI disclosure](AI-USE.md), and [Part 1 report](report.md). The report includes the application commit and a public [56-second demonstration](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/docs/demo.mp4). Only `report.md` should be uploaded to Canvas. Remaining implementation and evidence limitations are identified in the report.

## Sources

- [Yahoo streaming through yfinance](https://ranaroussi.github.io/yfinance/reference/yfinance.websocket.html)
- [yfinance usage and limitations](https://pypi.org/project/yfinance/)
- [Lightweight Charts documentation](https://tradingview.github.io/lightweight-charts/docs)

Quotes are sampled observations; the resulting candles and volume are not exchange-certified OHLCV. yfinance is independent of Yahoo and intended for research/education; consult its data usage terms. Lightweight Charts™ is by TradingView, Inc.: https://www.tradingview.com/. Its attribution logo is enabled in the chart.
