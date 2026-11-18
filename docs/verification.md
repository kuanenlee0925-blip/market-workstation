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

After migration and live checks, a direct comparison against that backup found all 12,090 original rows present and zero changed/missing payloads, digests or source/receipt timestamps. A limited credential-pattern scan of the staged source/text files found no matching tokens or private-key patterns.

## Real-provider observations

The bounded diagnostic after the listening-loop correction received BTC-USD price 73,307.71, source timestamp 1794338054000 milliseconds, receipt timestamp 1794338057.3198414 seconds, and provider day_volume 27405950976. The connection opened and the diagnostic exited normally. This was a separate real Yahoo observation, not a synthetic fixture or a profit claim. The field is a cumulative provider total, not trade size.

The separate live-provider Chromium check subsequently passed: it required a new SQLite receipt after test start, compared the rendered latest BTC-USD price with the saved quote after disconnect, verified Yahoo offline while the browser stayed connected, replayed recorded observations, and reconnected Yahoo. This is a deliberate upstream disconnect/reconnect observation, not an induced unexpected network/provider outage. A prior rerun timed out waiting for the initial chart while the database had a fresh receipt; a separate browser inspection showed valid snapshots and no page errors. The initial chart wait was increased to 15 seconds and the check reran successfully; the exact timing cause was not established.

Current production UI screenshots at 1440px and 390px were inspected and saved under `docs/screenshots/`. The original layout and palette remain, with the extra controls in the toolbar and source panel. The mobile inspection found no page errors or horizontal overflow.

Final local backend rerun: 18 passed. The final SmokeTest also reopened the persisted fixture database after restarting FastAPI with Yahoo disabled, replayed the selected range twice in a new browser, confirmed close 101/volume 11, and verified all 4 stored records remained unchanged. Both the initial integration phase and the post-restart replay phase passed; the optional real-provider test was skipped only in this offline command. Application commit: `100e41df29c335a31fe5f9b98959fedc23b45b46`.

## Updated video verification

The student's new November 10 recording was 89.17 seconds. The report now links a 58.17-second chronological excerpt copy, `docs/demo-2026-11-10.mp4`, at 1916 × 864 and 30 fps. Its metadata and representative edited frames were inspected. See evidence.md for the exact edit intervals. The clip shows source disconnect/unavailability; it does not show selected-range replay or successful feed recovery. Existing automated/live checks above remain separate evidence for those capabilities. No application tests were rerun solely for this media/documentation replacement.

Earlier November 9 observations and the original recording remain documented in evidence.md. They do not establish that newly added controls or fixes appeared in that recording.

## November 17, 2026 — Part 2 start: SMA

Implemented initial completed-candle SMA lines and crossover markers, configured through the chart. The Python reference test observed (short, long): warm-up (unavailable, unavailable), (11.5, unavailable), (8.5, 10), (10, 10), (16, 13; up), (13, 13), (4, 9; down). Prefix-by-prefix calculation matched the full calculation, and an unfinished candle did not signal. This is a calculation test, not a browser replay/revision verification.

Baseline backend: 18 passed. After changes: 24 passed, 5 existing dependency warnings. Frontend production build passed. SmokeTest failed before browser interaction: Playwright's expected chromium_headless_shell-1254 executable was absent. Health checks passed first; failure reporting also hit a Windows cp1252 UnicodeEncodeError. No browser was installed. The two marker browser inspection and replay with revisions remain unverified. A command to adjust reconnect behavior initially used the wrong working directory and failed; the correction was applied from the project root and the build passed afterward.

### Browser installation and follow-up

With student approval, ran `npx.cmd playwright install chromium` in frontend on Windows, using the existing Playwright installation. It installed Chromium and headless shell 158.0.8127.18 (revision 1254), FFmpeg and Winldd into the user Playwright cache; no project manifests changed. Expected browser launch was confirmed by the following SmokeTest. With `PYTHONUTF8=1`, SmokeTest passed the existing Part 1 browser, proxy failure/recovery and restart replay checks. This test does not inspect SMA markers. A new backend websocket replay test supplied the seven reference closes and a further observation to complete the final bar; it observed the expected two signals and no early signal. Backend suite: 25 passed, 5 warnings. Browser inspection of the crossover markers and replay with revisions remain outstanding.

### Configurable indicator start

Added named SMA and rolling range settings in SQLite, exposed their types and values through FastAPI/websocket, and added dashboard controls. Calculations use completed candles and price units; warm-up values are unavailable. The automated API/calculation check observed Range 2 = 5 and Range 3 = 6 for the supplied fixture, rejected zero, and reopened the same SQLite database to find both configurations. Backend suite: 26 passed, 5 warnings; frontend production build passed. The requested browser fixture/refresh check has not yet run; nor has a browser inspection of SMA crossover markers. The existing paired-SMA calculation has not yet been refactored to use the new indicator interface.

## Agent SDK setup check — November 17, 2026

Requested Activity 4 specifies openai-agents==0.24.0 and openai==3.52.0. On Windows, backend `.venv\Scripts\python.exe` is Python 3.14.7. Neither distribution was installed; `pip check` reported no broken requirements. A pip dry-run resolved both versions, including a change from websockets 17.4 to 16.1.1 and additional transitive packages. A successful dry-run is not an import or runtime compatibility test. No packages were installed in this check. Existing app has no rule lookup or Decision API implementation yet; those Activity 4 prerequisites remain to be built.

## November 17 — Activity 4 implementation

Student approved the exact SDK installation and websockets change. Installed with `.venv\Scripts\python.exe -m pip install openai-agents==0.24.0 openai==3.52.0`. Imports AsyncOpenAI/Agent/Runner/function_tool succeeded; installed versions printed 3.52.0/0.24.0. `pip check` before and after reported no broken requirements. Existing environment reused; websockets changed from 17.4 to 16.1.1. Dependency pins and observed lockfile updated. Backend restart is required.

Implemented read-only SDK agent, rule lookup, image-based Decisions helper, append-only stored chat turns and frozen rules/snapshots. Added chat UI, expandable actual tool results, captured chart preview, New chat and chart-result/marker binding. Rules live in backend/decision_rules.json. Existing Yahoo/candle/replay ingestion was not changed for the agent. Screenshot and supplied prompts are recorded in prompts/15-activity-4-chart-assistant.md and docs/chart-assistant.md.

Observed final backend check: 30 passed, 4 existing pandas warnings. Frontend build passed in frontend. An attempted build from the project root first failed because there is no root package.json; rerunning in frontend succeeded. Early offline SDK tests failed because direct tool invocation now requires ToolContext rather than RunContextWrapper; the test harness was corrected, and tools themselves ran successfully. A diagnostic import used a nonexistent SDK type-module name; the actual decision.py type definitions and official guide were checked instead. No production code relies on that failed import.

SDK tests verify registered names/input schemas, rule lookup without assessment, missing-key and controlled provider-timeout errors without invented WAIT, named choice/probability parsing, image input, conversation filtering and saved records. Browser tests use explicitly labeled controlled responses, not a live model. They exercise rule-only UI, assessment/tool display, captured PNG, same-conversation ID, New chat and mobile overflow. Desktop/mobile PNGs were visually inspected. Visual review found and corrected a stale marker on New chat; prior markers are excluded from new captures. Full SmokeTest passed after SDK installation, exercising the new browser fixture and existing proxy/restart/SQLite replay checks.

No backend OPENAI_API_KEY was configured (checked presence only). No real provider chat or chart-decision call ran. The full three-question course demonstration across two chart times and real tool selection still needs credentials/provider access. An ignored local .env template is present for private configuration; no key was printed or saved in source. Screenshots show synthetic data/controlled fixture responses and cannot be used as real-provider evidence.

## Real model connection attempt — November 17, 2026

Student configured the ignored backend .env. Presence was checked without exposing the key. A real SDK rule-question request in an isolated temporary SQLite store failed with RateLimitError before any tool ran. A separate direct Responses diagnostic with retries disabled returned HTTP 429, code credit_balance_exhausted, type insufficient_quota. No rule answer, assessment choice or probability was returned. No further live calls were attempted after diagnosing the billing condition. Current block is API credits, not a missing key. Added specific quota feedback to the assistant and decision error paths; no fallback decision is fabricated. Earlier statements that no key was configured describe the earlier state, not this latest attempt.
Backend regression check after quota-feedback change: 30 passed, 4 existing pandas warnings.

## November 18, 2026 — Part 4.2 scope and implementation

The supplied assignment overview clarifies that Part 2 requires indicators, simulated trading/accounting and backtesting; AI is Part 3 and not a prerequisite for Part 2. The supplied overview is saved under prompts/16-assignment-overview-and-part2.md. No new dependency was installed for Part 2. Existing Windows .venv Python3.14.7, Vue, FastAPI, SQLite, pandas, Playwright and installed Playwright FFmpeg were reused.

Added one event-driven long-only paper engine, manual pending orders/rejections/retries, transactional fills, weighted-average cost, per-event P&L, persistent strategies and frozen historical runs. SMA calculation now shares the generic indicator interface. Browser controls preserve the terminal structure; explicit synthetic/test labels distinguish fixtures. Documentation is in docs/part2-design.md. The prior Part 1 report was copied to docs/report-part1-archive.md before report.md became the Part 2 draft.

Observed backend: 36 passed, four existing pandas warnings. Independent pandas rolling means and the supplied reference agree; batch/prefix SMA and strategy outputs agree, including warm-up and ties. The reference strategy uses additional observations to fill buy4 at1 and close4 at9, cash1032. The known manual account shows cash600/4shares, unrealized40 at110, sell1 at110 -> cash710/realized10/unrealized30, value95 -> unrealized-15, close3 at105 -> cash1025/realized25. Tests cover idempotent requests/prefix processing, insufficient cash, rejected empty sales, out-of-order/correction fill exclusion, preserved earlier decision/fill/P&L evidence and SQLite reopening.

Frontend production build passed. Offline SmokeTest passed required SMA reference inspection, saved backtest reload, invalid settings without deleting a valid result, manual controls/known prices, retry/no extra fill, rejected empty sale, mobile width and no browser page errors. Existing Part 1 proxy/replay/restart checks remain. Added exact before/after comparison of all paper ledger/backtest-input tables and a browser paper-account check after restart. CI workflow already runs backend/build/SmokeTest on push and PR; no new remote run is claimed before commit/publication.

Visual review found the chart retained its old visible range when switching to the seven-candle reference, hiding one arrow; snapshots now fit the selected chart. Both arrows and numeric values were then inspected in video frames. Visual review also found an invalid text-encoding character introduced during a Windows edit; PaperPanel.vue was normalized to UTF-8 and test-source labels corrected. A read-only backup comparison command initially failed due to shell quoting; its here-string rerun succeeded. Before loading the new paper schema in the local app, a consistent ignored SQLite backup market.pre-part2-20261118-111553.sqlite was created. Comparison preserved all 38,912 original observation rows with zero changed/missing fields (identity,revision,symbol,source/receipt times,price,volume,payload,digest,supersedes). Fresh receipts may be added independently by Yahoo. The running localhost backend was restarted successfully and /api/paper/accounts returned healthy.

## November 18 — actual Part 2 recording and recorded-data result

scripts/record_part2_demo.py + frontend/scripts/record_part2_demo.mjs started an isolated backend with Yahoo disabled, copied 600 actual previously recorded BTC-USD observations read-only into a disposable database, and recorded real browser actions. No chart/provider results were mocked in this recording. The first scene uses the clearly labeled synthetic seven-close/reference backtest; the later scene uses recorded Yahoo historical arrivals, not a new live provider observation. The disposable service/database was cleaned up, leaving only the recording/result artifacts.

Observed recorded run: initial100000, order size1, SMA2/3, 1m; 21 fills, cash36299.73, quantity1, average cost62957.76, realized-742.51, unrealized14.63, equity99272.12, return-0.72788%, sampled max drawdown0.8189017547%. The final mark was62972.39 on completed candle2026-11-18T16:09:00Z. Summary/orders/fills and first/last signal availability are in docs/part2-recorded-result.json. A preliminary run using1000 cash and4-share size correctly produced no fills because BTC purchases exceeded cash; this was not represented as strategy profitability.

The saved VP9 WebM is docs/part2-demo-2026-11-18.webm: 51.84 seconds, 1440x1000, 25fps. FFmpeg metadata inspection and representative frames at6s/35s confirmed two SMA arrows and the losing recorded-backtest result. File SHA-256:771DB2A486DF4C6A2C0391C080E3B280E3C3AC696569E88E91C97BDC97A90186. A later small UI change adds input-hash/range metadata and clearer test labels; the recording predates those text-only refinements. It does not show every manual rejection/restart case; automated browser/database checks provide that separate evidence. Public availability is not yet verified because this work has not been committed/published. report.md clearly marks those fields pending and must not be submitted as final yet.

Final strengthened restart phase passed: both persisted offline replay and persisted paper-account browser checks, with exact equality of all ledger/backtest-input tables across the backend restart. Backend final36 passed; production build passed. No public commit/push/Actions/link verification occurred. report.md remains a draft pending review/publication.

## November 18 — approved publication

Student explicitly approved committing and publishing after the change summary/report/video review. Application commit07756dab80de868227d22efbec2780c60651c1fa was pushed to origin/main. A candidate-file scan found no long API-key/private-key patterns; local .env and SQLite/backups remain ignored. No credentials, local databases or dependency directories were staged. Unauthenticated GitHub metadata confirmed the repository is public. The published video returnedHTTP200,8497904bytes, SHA256771DB2A486DF4C6A2C0391C080E3B280E3C3AC696569E88E91C97BDC97A90186, matching the local artifact. GitHub served it as audio/webm, but an unauthenticated Chromium video element loaded it successfully with51.84seconds duration and1440x1000 dimensions. The report now pins supporting links to the reviewed application commit. A documentation follow-up records the commit reference and publication checks without changing application behavior.

GitHub Actions run44347105997 for application commit07756dab80de868227d22efbec2780c60651c1fa completed successfully. The clean Ubuntu runner passed dependency installation, backend tests, Vue production build, browser installation and full SmokeTest, including the restart phase. Report.md links that specific successful run. The next commit is documentation-only (report, README, verification and handoff).
