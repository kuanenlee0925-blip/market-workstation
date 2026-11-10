# Part 1 design and pipeline

Scope: prompts 01–09 including 07A; later indicators/trading/AI/voice prompts are reference only. Root: `C:\Users\kuane\OneDrive\Documents\ChatGPT\Market Workstation`. The existing Vue/FastAPI/SQLite stack and student-designed terminal layout are retained. The existing `.venv` is reused.

```text
Yahoo -> yfinance AsyncWebSocket -> Feed lifecycle -> Store.ingest -> SQLite
                                                          |
SQLite arrivals + explicit correction links -> minute_candles
                                                          |
                                         session-aware aggregation
                                                          |
                         REST history / browser WebSocket snapshots+deltas
                                                          |
                     Vue adapter -> candlesticks + volume + source/replay UI

Labeled CSV -> the same aggregation -> Synthetic CSV sample view (no DB writes)
```

## File responsibilities and transport

- `backend/store.py`: SQLite schema/migration, validation, exact-repeat suppression, append-only observations and explicit correction links.
- `backend/candles.py`: six-field OHLCV records, UTC time conversion, CSV reading, minute formation, exchange sessions, higher timeframes, and separate metadata.
- `backend/feed.py`: Yahoo connection lifecycle, retries, transport-state monitoring and deliberate disconnect/reconnect.
- `backend/main.py`: health/status/history/observations APIs, feed controls, browser snapshots/deltas, replay selection, and static built frontend.
- `frontend/src/App.vue`: chart adapter, live watchlist, timeframe/range controls, candle inspection, replay and source transparency. Existing three-column layout and palette remain.
- `scripts/smoke_test.py`: isolated local services, real browser/API/SQLite verification and cleanup. `scripts/check_yahoo.py`: bounded, real-provider diagnostic.

`GET /api/health` returns static health JSON; Vite proxies `/api` and `/ws`. `GET /api/history` defaults to the labeled synthetic CSV source and returns only `timestamp,open,high,low,close,volume` per candle. Use `source=recorded&symbol=AAPL&interval=5m` for saved observations. `with_metadata=true` returns the bars plus completion/coverage metadata. `X-Data-Source` identifies the history source. `/api/status` reports provider lifecycle independently of the browser socket. `POST /api/feed` takes `{ "enabled": false }` or true. This is a localhost application with no external deployment or real orders.

## SQLite and corrections

`observations` holds arrival `sequence`, legacy `identity` and `revision` ordinal, symbol, UTC source/receipt seconds, price, nullable cumulative volume, decoded source JSON, digest and nullable `supersedes` reference. Index: `(symbol, source_time)`; uniqueness: digest and `(identity, revision)`.

On opening an older database, add the nullable `supersedes` column without deleting or rewriting prior rows. The legacy revision ordinal is not proof of a correction. All old rows remain distinct unless an explicit correction link exists. Original database backups are kept locally and ignored by Git.

Yahoo does not supply a trustworthy universal correction/trade ID in these messages. Different payloads sharing a timestamp are therefore distinct observations. Exact canonical payload repeats are ignored. A caller with established correction evidence can explicitly reference the prior sequence through `Store.ingest(..., supersedes=sequence)`; only that link removes the older value from derived bars, never from the stored audit trail. Correction retransmissions are idempotent. Production Yahoo ingestion never guesses a correction solely from a timestamp. Identical messages cannot distinguish a retransmission from an indistinguishable new event; that source limitation remains.

## Candles, volume and sessions

Source order is `(source_time, arrival sequence)`; explicit corrections are resolved only within the available arrival cutoff. Bars use UTC ISO timestamps at interval starts. Candle objects contain exactly the six CSV fields. Completion, expected/observed minute counts, coverage flag, volume-known flag, session open and interval end are separate metadata keyed by candle timestamp. Ended means the interval ended, not that all market events were received; late data may revise it.

Volume is a delta of cumulative totals within a session. A missing baseline, missing total, reset/decrease, or multi-minute gap makes the affected minute's total unknown (`null`), not zero. A known unchanged total can produce a known zero. Once any constituent minute volume is unknown, its aggregate volume is unknown. Unknown histogram bars are gaps and textual values say Unknown. No synthetic gap prices or volume are created. Even known deltas are sampled approximations: quotes around a minute boundary cannot establish exchange-certified traded volume.

For AAPL/MSFT/SPY, `exchange-calendars` XNYS defines the common US equity regular session, holidays, DST and early closes (configured 2000–2035). Quotes outside that session are retained but excluded from regular-session candles. Intraday groups align to session open; daily bars start at session open, including on shortened days. BTC-USD uses 24-hour UTC days. Coverage means presence of each expected base minute; it does not certify a complete trade tape. CSV samples have known supplied minute volume and the same session aggregation.

## Replay and UI

Range inputs are UTC; start is inclusive and end exclusive. The selected source-time range filters base minutes before larger aggregation, so boundary bars may show partial coverage. Recorded events are frozen when replay begins. The replay advances one original arrival per second between the first and last matching arrivals, including intervening arrivals needed for correct late-data/baseline visibility. Earlier-arriving context supplies available baselines. Nothing after the displayed arrival cutoff is used. The current arrival's source and receipt times and sequence are displayed separately from the newest source time used for freshness. Completion uses recorded receipt time. Replay never inserts/changes records.

`FEED_ENABLED=0` starts with no Yahoo connection; saved replay remains usable. The Disconnect Yahoo button closes the upstream without closing browser sockets; reconnect opens a new upstream. A quiet open feed is distinct from a closed transport and source age remains visible. Browser WebSockets send a full snapshot initially/on selection changes, then changed candles/removals plus metadata. Vue updates current candles in place and rebuilds data for historical revisions/removals. Four additional read-only watchlist sockets remain live independently of the main replay view.

## Boundaries

No indicators, accounts, strategies, backtests, model decisions, vision or voice are implemented in this Part 1 scope. Source collection is unbounded and aggregation currently reads a symbol's saved history; long-running operation will need bounded/indexed aggregation. Tests use isolated databases; fixture ingestion routes exist only with `MARKET_TEST_MODE=1`, not in ordinary operation. Live-provider checks are separate from deterministic SmokeTest.
