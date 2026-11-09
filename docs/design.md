# Current architecture

Yahoo Finance → yfinance AsyncWebSocket → validation → SQLite → FastAPI WebSocket snapshots → Vue → Lightweight Charts candlestick and histogram panes.

The backend subscribes to four fixed symbols at startup, retries failed connections, and sends browser snapshots every second. The source has its own update cadence. A quiet feed stays in waiting state; historical source age remains visible after updates stop. Browser connection state is separate from upstream state. The database persists across restarts.

## Schema and identity

`observations`: sequence (arrival order primary key), identity (Yahoo, symbol, source timestamp), revision, symbol, source_time (UTC epoch seconds), received_time (UTC epoch seconds), price, day_volume (nullable cumulative volume), payload (original decoded JSON), digest (unique SHA-256 of canonical payload). Unique (identity, revision). Index on (symbol, source_time).

Yahoo streaming does not provide a universal trade identifier. Identity is a documented heuristic: symbol plus source timestamp. Distinct updates with that identity are revisions, even if the source actually produced two distinct quotes at the same timestamp. Exact payload duplicates are ignored, retaining the first receipt. Revised payloads append a version. Original observations are not deleted. SQLite commits before the next browser snapshot.

## Candles and volume

Bars group latest revisions by source minute in source-time order. Late observations rebuild earlier bars. The first/last observed quote supplies open/close; max/min supplies high/low. No gap candles are fabricated. Complete means the minute has ended according to the backend clock, not that every market event was received; completed bars may still revise on late arrivals.

Yahoo day_volume is cumulative. Volume is the positive delta between successive observed totals, assigned to the newer quote's minute. The first total is excluded and decreases reset the baseline. Missing totals contribute zero. Feed gaps can move multiple minutes' volume into one minute; cumulative semantics differ across instruments, especially crypto. These values are observed deltas and are not authoritative exchange volume.

## Replay and boundaries

Replay fixes the current list of arrivals and advances its sequence cutoff once per second. At each step, revisions and late observations are visible only if already received. Completion uses recorded receipt time. The replay is a view of stored observations, not a strategy backtest. The live recording continues while a browser replays. Data age always uses today's clock and the displayed source timestamp, so old replay data is visibly old.

There is no historical bootstrap, CSV loader, indicator, order execution, backtest, model, vision, or audio integration in this stage. Full snapshots and in-memory aggregation suit a small course demonstration; long-running high-volume recording will need bounded queries and incremental aggregation. No database pruning is implemented.

## Reference-inspired workstation interface

The interface uses a compact navigation bar, live ticker, searchable watchlist, central chart, recorded-performance sidebar, and recent-minute activity cards. Teal and orange distinguish rising/falling candles. Watchlist buttons and ticker symbols select the chart; search filters the supported watchlist. Fit chart restores the visible recorded range. Narrow screens stack these panels.

Four additional read-only browser WebSockets keep the watchlist live while the selected chart can replay independently. These connections read the existing backend and do not create additional Yahoo subscriptions. Changes are measured from the first recorded bar's open to the latest close, not from the previous trading day's close. Range and volume summaries describe the selected chart's current view, including its replay cutoff. Recent activity cards summarize recorded candles, not news or AI analysis. No fundamentals, analyst ratings, earnings, or forecast data are fabricated to fill reference-image panels.
