# Chart assistant

The read-only assistant uses OpenAI Agents SDK 0.24.0 with OpenAI Python 3.52.0. It appears below the chart and follows the existing terminal palette and responsive layout. It cannot place orders.

Copy `.env.example` to `.env` and set OPENAI_API_KEY privately on this computer. Restart FastAPI after configuration changes. Never paste a key into chat or commit it. `OPENAI_CHAT_MODEL` and `OPENAI_DECISION_MODEL` default to gpt-6-luna. The saved workstation can open offline; new chat replies and chart assessments need an API connection and provider access.

Each Send creates a browser PNG and copies the displayed bars, symbol, interval, market mode, chart timestamp, source timestamp and receipt timestamp. The backend assigns a snapshot ID. Captures exclude previous indicator/decision markers. The current question and choice definitions are loaded from `backend/decision_rules.json` and frozen for that message. These are educational direction labels and do not represent executable short positions.

`read_decision_rules` returns the definitions. `assess_chart` sends the frozen image/context to `/v1/decisions` through AsyncOpenAI. Only the actual named choice and returned confidence become the chart result. Missing credentials, insufficient completed candles, timeouts, malformed answers and refusals remain errors. The SDK runner selects tools; no keyword routing simulates a model. Tool traces and results are shown separately from the assistant's prose. Tracing to the provider's agent trace service is disabled.

SQLite `chat_turns` preserves requests, captured images, frozen rules, responses and tool results. Existing turns are not overwritten. Context includes up to 12 previous turns of the same symbol and mode in the conversation. New chat starts a fresh conversation; it retains old evidence in SQLite. The history is currently maintained through the backend conversation ID in the open page; reloading starts a new visible chat. A full chat-history browser is not implemented.

The chart result and marker update from the tool result only if the symbol, mode, interval, range and displayed bars still match. Older results remain readable in their chat turn. An ongoing live chart may change before the model finishes; that result then stays in history rather than appearing on changed candles. Probability is choice confidence, not a profitability estimate.

Verification: automated SDK tools, controlled provider contract/error checks and labeled browser response fixtures are offline checks. No real provider request has run because no backend API key was configured. Complete the three course questions against two different snapshots once credentials and model access are available. Check both returned chart times, tool names, probability and marker; save actual evidence without substituting fixture results.

Sources checked: https://developers.openai.com/api/docs/guides/agents/quickstart and https://developers.openai.com/api/docs/guides/decisions .
