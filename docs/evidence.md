# Curated evidence log

## November 9, 2026 — initial Part 4.1 implementation

- Intent: implement the first cumulative stage using the supplied assignment and references.
- Instruction excerpt: after being offered “start implementing Part 4.1” or a development plan, the user replied “yes”; implementation of Part 4.1 was the stated working assumption.
- Generated files: `backend/store.py`, `backend/main.py`, `frontend/src/App.vue`, and companion configuration/documentation.
- Design decision: retain an append-only arrival sequence and revisions so replay cannot see future corrections; source timestamp identity remains a heuristic.
- Verification: see subsequent entries below for actual command and live-provider results. Unit tests use synthetic observations and do not establish Yahoo availability.
- Initial reference-access limitation: automated retrieval of TradingView's chart page failed; Finnhub's API page returned no readable text. yfinance and Lightweight Charts documentation were readable. Finnhub is not implemented.
- Remaining uncertainty: live source coverage, sampling gaps, instrument volume semantics, and final submission/video/repository access require explicit evidence.

## Verification results — November 9, 2026

- `python -m pytest backend -q`: **4 passed**. Synthetic cases verify duplicate suppression, revision visibility at a replay cutoff, late quote ordering, candle completion, cumulative-volume reset, persistence after reopening, and invalid-price rejection.
- `npm.cmd run build`: passed (Vue and Lightweight Charts production bundle).
- `LIVE_TEST=1 npx playwright test`: **2 passed**. Chromium exercised an explicitly mocked unavailable feed, empty state, symbol selection, replay command, and a 390px viewport without horizontal overflow. A separate unmocked test rendered actual BTC-USD observations, entered recorded replay, and returned to live mode without browser JavaScript errors.
- `/api/status` reported Yahoo connected. Direct SQLite inspection at that check found 31 AAPL, 31 MSFT, 31 SPY, and 6 BTC-USD arrival/revision rows. Counts are a point-in-time observation, not fixed fixtures. These observations traversed the actual Yahoo → yfinance → backend → database path; browser rendering was also checked.
- Screenshot `frontend/test-results/dashboard.png` was visually inspected locally (generated test output, excluded from Git). It shows the recorded-replay view, source monitor, chart panes, and simulation label. This is not the required submission video.
- Revised implementation: yfinance source inspection showed its async listener consumes cancellation during cleanup. The stream loop now checks task cancellation after listener exit, so shutdown cannot accidentally start another connection. This code path is inspected, not claimed as a separately tested provider failure.
- Dependency-install timing: initial backend launches failed while pip was still installing. After installation completed, startup and live checks succeeded; no application fallback was used to conceal the failure.
- Unavailable-feed browser evidence is mocked; an actual provider outage/recovery was not induced. Long-running scale, clean-checkout reproduction, and classroom access/video remain unverified.

## Reference screenshot redesign — November 9, 2026

- Request: “make it like this,” with a dark three-column financial-terminal screenshot.
- Result: `frontend/src/App.vue` and `frontend/src/style.css` now provide a compact header/ticker, searchable live watchlist, teal/orange candlestick chart, recorded range/performance panels, source timestamps, and candle activity cards. Existing live/replay behavior remains.
- Decision: use recorded-price summaries and source metadata in the reference's sidebar/card positions rather than invent fundamental data, news, or forecasts.
- Verification: production build and all 4 backend checks passed. The updated default Chromium check passed, exercising unavailable state, replay, symbol switching, watchlist search/click, chart fit, and 390px width. Real-data screenshots at 1440px and 390px were visually inspected; the mobile page had no horizontal overflow. Local screenshots are in `frontend/test-results/redesign-desktop.png` and `redesign-mobile.png` (generated, excluded from Git).
- Limitations: four supported instruments remain; charts reflect data recorded since local collection began. Percent changes are labeled as recorded-period changes. The watchlist remains live while the main chart replays.
- Final live-provider rerun: both Chromium checks passed with `LIVE_TEST=1`; Yahoo status was connected. The first rerun exposed an outdated exact-text selector after the mode label gained adjacent interval metadata. The check now targets the chart footer and verifies its mode text; the application behavior required no change. Test screenshots are ephemeral and may be replaced by later Playwright runs.

## GitHub publication and clean checkout — November 9, 2026

- Request: “do the github for me.” Repository: `kuanenlee0925-blip/market-workstation`, created private. Local database, installed dependencies, generated build/tests, and environment files are excluded. A credential-pattern scan of the 23 publishable files found no matching private keys or token patterns; this is a limited check, not a general security audit.
- Application commit: `92dcd5c5352b92d4ee65fd83e636c01c3dc251fe`. A subsequent documentation-only commit records its ID and these results.
- A separate clean local clone passed fresh `npm ci`, production build, and all 4 backend tests. Its server started on a separate port, automatically initialized a separate SQLite database, served the built frontend with HTTP 200, and returned a valid AAPL WebSocket snapshot. Git status remained clean after these operations.
- Backend checks used the already installed Python environment; a fresh Python environment was not reinstalled. This clean-checkout startup check did not establish a new live-provider observation. Earlier live-provider results are documented separately.
- Remaining submission work: instructor access to the private repository and a real accessible demonstration video link.
