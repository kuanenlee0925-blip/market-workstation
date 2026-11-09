# Part 4.1 — submission draft

Implemented a local Vue/FastAPI/SQLite workstation with Yahoo WebSocket ingestion, candlestick and observed-volume panes, source age and connection state, append-only observation revisions, and arrival-order replay.

Design and limitations: [design notes](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/docs/design.md). Verification/process evidence: [evidence log](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/docs/evidence.md). Tool disclosure: [AI-USE.md](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/AI-USE.md). Startup: [README](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/README.md).

- Repository URL: https://github.com/kuanenlee0925-blip/market-workstation
- Submitted commit: **TO BE ADDED**
- Accessible demonstration video (30–60 seconds): **TO BE ADDED**

Verification: 4 backend tests passed; production build passed; 2 Chromium browser tests passed, including an actual Yahoo/BTC-USD data path and replay. The unavailable-feed browser case uses an explicit mock. See the evidence log for limitations.

This draft is incomplete until submission links and clean-checkout verification are supplied. No simulated account, indicators, backtesting, or AI features are claimed for this stage.
