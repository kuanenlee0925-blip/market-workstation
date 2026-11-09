# AI-use disclosure

On November 9, 2026, OpenAI Codex in the desktop app assisted with assignment interpretation, Vue/FastAPI/SQLite implementation, tests, and documentation. The user supplied the assignment and reference links and agreed to begin Part 4.1. The exact underlying model identifier was not provided to the project; do not infer it from the application name.

Generated code includes `backend/store.py` (observation revisions and candle construction), `backend/main.py` (source and browser sockets), and `frontend/src/App.vue` (dashboard). The student must inspect this code, verify behavior, and update this disclosure for subsequent tools or models. No model is integrated into the application at this stage.

The user subsequently supplied a trading-terminal reference screenshot and requested “make it like this.” Codex adapted the Vue layout and CSS, added a live watchlist and summaries derived from recorded candles, and updated the existing browser check for the changed controls. The screenshot guided visual layout and styling; its financial figures and panels were not copied as application data.

At the user's request, Codex also prepared Git commits, repository publication, and report links. Local Git commits use the account's GitHub noreply address. Authentication credentials, local databases, and installed dependencies are excluded from source control.
