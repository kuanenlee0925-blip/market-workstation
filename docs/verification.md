# Current Part 1 verification — November 10, 2026

Scope: supplied prompts 01–09 including 07A, with the existing UI preserved. Reference prompts were copied from the student's ZIP, not executed as a batch. No new Python environment was created. The student approved `.venv\Scripts\python -m pip install "exchange-calendars>=4.11,<5"`; version 4.13.2 was installed with its dependencies into the existing `.venv`. The requirement and observed environment record were updated. Calendar import/session checks passed: November 9 open 14:30 UTC, November 27 early close 18:00 UTC.

## Repeatable checks and expected results

| Command/check | Expected result | Observed result |
|---|---|---|
| `.venv\Scripts\python -m pytest backend -q` | Exact repeats suppressed, distinct same-time quotes retained, explicit corrections cutoff-aware, unknown/reset volume distinguished, sessions/timeframes correct, HTTP/WS behavior verified | 18 passed including two listener closure/cancellation checks |
| `npm.cmd run build` in frontend | Vue and chart imports resolve and production bundle builds | Passed |
| `.venv\Scripts\python scripts/smoke_test.py` | Real Vue/FastAPI/SQLite chain works on temporary ports/database, fixtures clearly labeled; fail if proxy is independent of backend or persistence changes | Two complete runs passed after the cleanup correction; the live-provider test was deliberately skipped in both |
| CSV second row and Inspect candle | November 9 14:31 UTC close 101, volume 850 | Verified through API and real browser |
| CSV higher timeframe | 5m O100/H105/L99/C104/V3550, coverage 3/5; daily coverage 3/390 | Verified through backend tests and browser |
| Prompt 7 quote example, middle observation arriving late | O100/H103/L100/C101/V11; provisional before minute end and complete afterward | Verified with constructed inputs, not claimed as live quotes |
| Two quotes at one timestamp | Prices 100 and 105 retained; open/low 100, high/close 105 | Backend check passed; no correction guessed from shared time |
| Missing baseline, reset or missing total | Unknown/null volume; known unchanged total can give zero | Backend checks passed; UI says Unknown and uses a histogram gap |
| Replay selected range twice with Yahoo stubbed/offline | Same final C101/V11 and unchanged saved observations; late-arrival source time is explicit | Real browser/API/SQLite check passed |
| Direct/proxied health and backend failure/recovery | Matching static JSON; frontend proxy returns an error when backend stops; recovery after restart | SmokeTest passed, including persistence of all 4 constructed fixture observations |
| Exchange sessions | Partial 5m/daily coverage; next session starts new daily bar; holiday excluded; early-close day 210 minutes; DST and hourly session alignment correct | Backend checks passed |

## Failures and revisions

1. Initial end-to-end SmokeTest passed UI/proxy/persistence checks but failed cleanup on Windows with an open SQLite file. Evidence: PermissionError during TemporaryDirectory cleanup. Cause: sqlite3 connection context managers commit/rollback but do not close connections. Correction: use `contextlib.closing` for the runner's inspection connections. Both subsequent runs cleaned up successfully.
2. The first real-provider disconnect check received fresh data but did not reach offline status. A bounded standalone diagnostic also did not finish cleanup. Source inspection showed yfinance 0.2.66 can loop after a clean close, and its cancellation behavior can hide closure from the application. Correction: isolate `YahooConnection`, reusing yfinance connection/subscription/decoder with a listening iterator that propagates closure and cancellation. Added bounded regression checks for those two paths. This adapter depends on private yfinance transport/decoder attributes and must be reverified on upgrades.
3. One restart shell command had a quoting error and did not stop the old server; the next startup correctly reported port 8000 already in use. The command was corrected and only identified project server/diagnostic processes were stopped. No observations were deleted.

## Database preservation

Before changing the running application, the existing 12,090 observations were backed up locally to an ignored `market.pre-prompts-20261110-141047.sqlite`. Migration adds nullable supersedes links and does not rewrite prior payloads, source/receipt timestamps, digests or sequences. A disposable legacy-schema migration check verifies both same-time rows remain. Old revision ordinals are treated as legacy ordinals, not correction evidence.

## Real-provider observations

The bounded diagnostic after the listening-loop correction received BTC-USD price 73,307.71, source timestamp 1794338054000 milliseconds, receipt timestamp 1794338057.3198414 seconds, and provider day_volume 27405950976. The connection opened and the diagnostic exited normally. This was a separate real Yahoo observation, not a synthetic fixture or a profit claim. The field is a cumulative provider total, not trade size.

The separate live-provider Chromium check subsequently passed: it required a new SQLite receipt after test start, compared the rendered latest BTC-USD price with the saved quote after disconnect, verified Yahoo offline while the browser stayed connected, replayed recorded observations, and reconnected Yahoo. This is a deliberate upstream disconnect/reconnect observation, not an induced unexpected network/provider outage. A prior rerun timed out waiting for the initial chart while the database had a fresh receipt; a separate browser inspection showed valid snapshots and no page errors. The initial chart wait was increased to 15 seconds and the check reran successfully; the exact timing cause was not established.

Current production UI screenshots at 1440px and 390px were inspected and saved under `docs/screenshots/`. The original layout and palette remain, with the extra controls in the toolbar and source panel. The mobile inspection found no page errors or horizontal overflow.

Earlier November 9 observations and the original recording remain documented in evidence.md. They do not establish that newly added controls or fixes appeared in that recording.
