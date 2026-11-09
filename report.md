# Part 4.1 — submission draft

Implemented a local Vue/FastAPI/SQLite workstation with Yahoo WebSocket ingestion, candlestick and observed-volume panes, source age and connection state, append-only observation revisions, and arrival-order replay.

Design and limitations: [design notes](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/docs/design.md). Verification/process evidence: [evidence log](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/docs/evidence.md). Tool disclosure: [AI-USE.md](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/AI-USE.md). Startup: [README](https://github.com/kuanenlee0925-blip/market-workstation/blob/main/README.md).

- Repository URL: https://github.com/kuanenlee0925-blip/market-workstation
- Submitted application commit: [92dcd5c5352b92d4ee65fd83e636c01c3dc251fe](https://github.com/kuanenlee0925-blip/market-workstation/commit/92dcd5c5352b92d4ee65fd83e636c01c3dc251fe). A later documentation commit adds this reference and clean-checkout results; application code is unchanged.
- Accessible demonstration video (30–60 seconds): **TO BE ADDED**

Verification: 4 backend tests passed; production build passed; 2 Chromium browser tests passed, including an actual Yahoo/BTC-USD data path and replay. The unavailable-feed browser case uses an explicit mock. See the evidence log for limitations.

Clean-checkout verification passed: a separate local clone installed frontend dependencies with npm ci, passed the build and 4 backend tests, initialized its own SQLite database, served the frontend, and returned a WebSocket snapshot. Backend dependencies reused the existing Python environment; a fresh Python installation is not claimed.

The GitHub repository is public and can be accessed without an invitation. This draft still needs the accessible demonstration video link. No simulated account, indicators, backtesting, or AI features are claimed for this stage.
