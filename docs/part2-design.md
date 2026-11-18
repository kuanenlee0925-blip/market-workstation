# Part 2 — strategy, execution, accounting and historical evaluation

## Workflow

The workstation retains Vue, FastAPI, SQLite, localhost operation and Yahoo streaming. The watchlist/chart/sidebar structure and dark palette are retained. The panel below the chart provides simulated accounts and saved backtests. No real broker or order API exists. Part 2 does not use the AI assistant or require API credits.

1. Set the chart SMA windows (positive integers, short < long). Apply SMA. SMA reference displays the seven labeled synthetic closes from the supplied hand example; it is not Yahoo data. Inspect a candle to read both values. Yellow is short, purple is long, arrows mark confirmed crossovers.
2. In Simulated trading & backtesting, select starting cash, the strategy windows and order size. These are explicit settings for a new account/run, independent of the chart controls. The selected chart symbol and interval supply the new account's symbol/timeframe.
3. Create paper account. It starts flat with no prior fills. Manual whole-share buy, sell and close orders wait for eligible new Yahoo arrivals; chart replay and synthetic views disable the manual controls. Enable SMA strategy to buy a fixed quantity on an up crossover when flat and close the entire holding on a down crossover. A pending order prevents an additional strategy order. Pausing stops new strategy decisions; it does not cancel accepted pending orders. Multiple explicitly enabled accounts can run independently.
4. Run backtest uses either the labeled synthetic reference or recorded Yahoo arrivals. The UTC start/end fields filter receipt times (start inclusive, end exclusive). Each run is a new immutable account, not a reset of an earlier account. The selected range starts with fresh warm-up. No final forced liquidation is performed.
5. Saved account/run reopens prior settings, orders/fills, equity/P&L history and signals after a page refresh or backend restart. Orders expose status and rejection reasons. P&L includes valuation source and separate source/recording times.

## Indicator contract

Python `calculate_indicator` consumes chronological six-field candles, completion metadata, type and a positive integer window. It returns a value or a warm-up/uncompleted gap at every candle timestamp. SMA averages the last N completed closes, including the displayed candle. Rolling range is max(high)-min(low) over N completed candles, in price units. The chart's paired SMA calculation uses this same interface.

No value or confirmed signal is emitted for an unfinished candle. Time-complete bars with incomplete coverage may still be used; their coverage remains visible. Missing minutes are not fabricated. First non-equal comparable SMAs establish a side; equality retains the last side, and only a subsequent side change emits an arrow. Comparison happens before display rounding. Calculations use Python numeric precision; money in account transitions uses Decimal, not display-rounded SMA values.

The supplied closes 13,10,7,13,19,7,1 with windows 2/3 give: third 8.5/10, fourth tie 10/10, fifth up at 16/13, sixth tie 13/13, seventh down at 4/9. An independent pandas rolling mean and the hand values are tested, alongside all prefixes. The first short value is 11.5 on the second candle; the long value remains unavailable until the third.

## Execution model and accounting

Paper accounts are long-only, whole shares, USD, zero fees, zero modeled spread or slippage, and no leverage. Cash is not reserved on acceptance. Sales larger than current holdings and invalid quantities are rejected. At fill time cash/shares are checked again; competing orders can therefore be accepted and later rejected. Close captures the quantity held at submission and rechecks it at fill. Request IDs are unique per account; an identical retry returns its original order, while conflicting reuse is rejected.

An order fills only on a later eligible observation sequence, at that observation's price. Receipt/event time must not precede submission. Manual orders require source time at/after submission. Strategy orders require source time at/after the signal candle's end. The observation must be in the symbol's session and must not move backward behind the source-time watermark. Explicit corrections cannot be executable new quotes. The arrival that first reveals a completed-candle signal cannot also fill that new order. There is no depth, liquidity/partial-fill model, broker latency or real execution claim. An order stays pending if no eligible quote arrives, including at the end of a backtest.

Weighted average cost = (old shares * old average + purchased shares * fill price) / new shares. Selling realizes sold shares * (fill price - average); partial sales preserve average. Closing resets average to zero. Unrealized P&L = open shares * (valuation price - average). Equity = cash + open shares * valuation price. A P&L row is recorded after every fill and when a newly completed candle values an open position. A valuation row identifies its event, availability time, price and source time. There are no deposits/withdrawals after account creation. If no usable price exists, an open holding's valuation is unavailable. Display rounding is separate from Decimal state; serialized numeric chart/report values use normal float precision.

## Replay and look-ahead boundaries

The engine reads original SQLite sequence order, not source-time-sorted future data. At each step it reconstructs candles only from that arrival prefix and revisions already visible at that cutoff. Event time is the running maximum of receipt times, so a backwards receipt clock does not rewind completion. Pending older orders fill before new decisions are submitted. Every completed-candle decision is recorded once with its available-at time, triggering observation sequence and SMA values. Late corrections can affect later calculations, but never rewrite old decisions, fills or valuations. Reprocessing a prefix is a no-op. Live accounts start at the latest stored sequence and skip already completed candles; existing history can warm their indicators without creating retroactive trades.

Historical runs freeze their exact input rows and SHA-256 in `backtest_inputs`. Their order/fill/P&L ledger remains separate from raw observations. The browser can replay market data without executing paper orders; automatic live accounts continue processing fresh Yahoo arrivals independently of the chart's view mode. Backtesting is bounded to 3,000 arrivals, and processing is synchronous for this local educational use. Long-running scale is not established.

## SQLite evidence

`paper_accounts` stores immutable configuration plus replaceable current derived state. `paper_orders` stores original requests; `paper_order_events` appends status transitions. `paper_fills` is unique by order. `paper_pnl` is unique by account/event key, and `paper_signals` by account/candle. A fill, its status, cash/shares/cost update and fill P&L commit in one SQLite transaction. Backtest input snapshots are separately retained. Current-state updates do not remove ledger history. The original observations and correction links are unchanged by trading/backtesting.

## Verification and interpretation

Known account: buy 4 at 100 -> cash600/qty4; value110 -> unrealized40; sell1 at110 -> cash710/qty3/realized10/unrealized30; value95 -> unrealized-15/total-5; close3 at105 -> cash1025/qty0/realized25/unrealized0. Retry, oversell, insufficient cash, duplicate processing, correction visibility and restart persistence have automated checks.

The synthetic reference backtest adds observations at 8 and 9 after the seven closes so signals have future fill opportunities. With 1000 cash and 4-share size, buy fills at 1 on observation7 and close fills at 9 on observation9, ending1032/realized32. These intentionally extreme test prices check timing, not plausibility or a market edge. Batch and incremental engine results agree.

The recorded-data demo uses 600 earlier Yahoo BTC-USD arrivals, 100000 starting cash, 1-share size, SMA2/3 and 1m candles. Observed: 21 fills; cash36299.73, one share at average62957.76, realized-742.51, unrealized14.63 at completed-candle mark62972.39; equity99272.12, return-0.72788%, sampled max drawdown0.81890%. See `part2-recorded-result.json` for the saved summary, orders, fills and available-at boundaries from that run. The demo's disposable database was cleaned up after recording; its raw inputs are not bundled in the public repository. Normal saved runs retain inputs in the ignored local application database.

This is one short historical sample of one surviving instrument. It establishes implementation behavior under these assumptions, not expected future profit. Selection/survivorship bias, overfitting after parameter exploration, quote gaps, revisions, latency, coverage and omitted costs limit interpretation. Sampled drawdown uses fill/completed-candle equity points plus initial cash; it does not measure every intra-candle move. No annualized risk metric, benchmark comparison, out-of-sample validation or optimization study is claimed.

The GitHub Actions workflow on push/pull_request installs declared dependencies, runs backend tests, builds Vue, installs its browser in CI and runs SmokeTest. A local pass is not evidence that a new remote Actions run has completed; inspect the submitted commit's run after publication.
