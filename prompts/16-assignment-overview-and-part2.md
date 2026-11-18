Individual · four equal-weight parts: three Canvas submissions and one live in-class presentation

Assignment 4 contributes 25% of the course grade.
Assignment 4 brings together the skills developed through the calculator, the simulated Expedia replica, and the mental health support bot. Students will build one local AI-assisted market workstation and trading bot, continuing the course practice of directing a coding agent, inspecting generated code, testing the running application, and explaining design decisions.

A market workstation helps a person follow changing prices, interpret patterns, and examine the consequences of a trading decision. A candlestick chart summarizes each time interval through its opening, highest, lowest, and closing prices; corresponding volume shows how much was traded. Indicators add derived information, while a simulated account makes the consequences of decisions visible.

The completed application connects observation, interpretation, action, and review. Its dashboard shows the market, its indicators provide a basis for decisions, and its trading simulation records the results. AI contributes decision support, chart-image interpretation, and conversation through text and live audio. Students must be able to explain how these capabilities work together and what their evidence establishes.
The central problem is to turn a changing, noisy stream of market observations into an understandable interface and an accountable decision-making process. The assignment has five connected concerns:
- Visualize domain-specific data. Use a charting library to present price and volume clearly and keep the dashboard understandable as new observations arrive.
- Coordinate live services and stored data. Connect multiple APIs, use WebSockets for real-time communication, and preserve useful records in a backend database.
- Create intelligence from data. Derive indicators and signals from price observations so that market behavior can be interpreted. This concerns calculated information, such as moving averages and crossovers; chart-image interpretation by a model has a separate role.
- Support AI-assisted decisions and automation. Provide relevant context to a model, check its response, and connect the resulting decision to a simulated trading bot. Text and audio interaction should help the user understand the application’s observations and actions.
- Account for simulated outcomes. Track trades, account state, and profit or loss, and use historical backtesting to examine how a strategy behaves over time.
The three implementation parts develop these concerns cumulatively. Students choose the interface and implementation within the requirements below; the evidence should make each connection understandable and verifiable.
Reference application. Explore [TradingViewLinks to an external site.](https://www.tradingview.com/chart/) as a reference for the workstation’s interface. Consider how it presents candlestick charts, volume, indicators, and market information, and which design choices would help make the student application understandable and usable.

Charting libraries. TradingView’s [Lightweight ChartsLinks to an external site.](https://github.com/tradingview/lightweight-charts) is one open-source option for financial charts in the browser. Students may choose another suitable library and should explain how it supports their dashboard.

Technical indicators. Indicators derive information from market observations. This assignment uses two simple moving averages and their crossover as the required starting strategy. Correct calculation and clear interpretation matter; an indicator is not a guarantee of a profitable decision.

The relevant definitions are:
- SMA (simple moving average). The arithmetic mean of the closing price over the last N bars, recomputed on each new bar. An SMA(20) on 5-minute candles is the average close of the last twenty five-minute bars.
- EMA (exponential moving average; optional). An average that assigns greater weight to recent prices. An implementation should document its formula and how the first value is initialized.
- SMA crossover. Calculate two simple moving averages over different window lengths. A crossover occurs when the shorter-window SMA moves from one side of the longer-window SMA to the other. A strategy can interpret an upward crossover as a buy signal and a downward crossover as a sell signal. For this project, show and explain how the crossover contributes to the simulated trading bot’s decisions.
- RSI measures the size of recent gains against recent losses on a 0–100 scale; MACD is built from the difference between two EMAs. Both are optional here and both are well documented.
A signal based on an unfinished candle can change as the price moves. The application must distinguish a provisional signal from one based on a completed candle.

Backtesting and its characteristic failures. Backtesting simulates a strategy on historical data. It differs from replaying recorded observations: a backtest also evaluates the strategy’s simulated decisions and outcomes. When evaluating a strategy, three common failure modes should be understood:
- Look-ahead bias — the strategy is evaluated using information that would not have been available at the moment of decision.
- Survivorship bias — the test universe includes only instruments that still exist.
- Overfitting — parameters are tuned until the strategy explains the historical sample precisely and generalizes poorly.
These problems can make a strategy appear more effective than the evidence supports. A historical result does not establish future performance.

Event-driven versus vectorized architectures. Two established structures are to process observations sequentially or compute across arrays. Either approach must restrict each decision to information available at that moment.

Existing platforms. Backtrader and QuantConnect provide examples of separating strategy logic from data processing. They are optional references; neither platform is required for this project.
Use the familiar Vue frontend, FastAPI backend, and SQLite database on localhost. Market-data, model, and live-audio services have distinct roles; students should explain what information each receives, what it returns, and how it connects to the rest of the application. Deployment and a mobile build are not required.

Yahoo Finance. Use Yahoo Finance for the live-streaming market-data portion of the project. The [yfinance packageLinks to an external site.](https://pypi.org/project/yfinance/) and its [documentationLinks to an external site.](https://ranaroussi.github.io/yfinance/) are a starting point. The package is an independent tool, not an official Yahoo library; its [WebSocket documentationLinks to an external site.](https://ranaroussi.github.io/yfinance/reference/yfinance.websocket.html) describes streaming price updates. Check the actual availability and timing of the chosen data and show its age in the application. A frequently refreshed display does not by itself establish that source data is current.

Other sources. Students may examine [FinnhubLinks to an external site.](https://finnhub.io/docs/api) or another source for comparison. The required live connection remains Yahoo Finance. Students should document the availability and limitations of their chosen data.

Market hours. The chosen instrument may not trade when development or a demonstration takes place. Recorded observations allow the application to be exercised when live updates are unavailable.

Bar formation. A candle for the current interval is incomplete until that interval ends. Its high, low, and close continue to change. Any calculation consuming the current bar is consuming a value that has not settled.
Parts 4.1–4.3 are cumulative submissions of the same application. Part 4.4 is its live in-class presentation. Students choose the charting library, interface, market instruments, SMA window lengths, and AI services, and explain those choices. Continue the browser-testing, Git/GitHub, documentation, and AI-use evidence practices established in the course.
Outcome: a working client-server dashboard with live-streaming market data and persistent records.
- Live visualization. Connect to Yahoo Finance and use a charting library to display updating candlesticks and corresponding volume. Use WebSockets for real-time communication. Make the data source, age, and feed status visible.
- Persistence and replay. Store market observations in SQLite so that they can be retrieved and replayed. Preserve observation identity, source and receipt times, revisions, and whether a candle is complete. Explain and test how duplicate, revised, and out-of-order observations are handled.
- Working evidence. Demonstrate the path from the live source through the backend to the chart and database, including an unavailable-feed condition. Maintain the README, agent instructions, and design notes describing the data flow and SQLite schema. Document database initialization and startup without exposing credentials.
CSV loading is ungraded in-class practice. The Part 4.1 deliverable must demonstrate live streaming. Recorded observations support development and replay when the market is closed.
Outcome: a workstation that derives signals and measures simulated trading outcomes.
- Indicators. Display two simple moving averages of different lengths and their crossover. EMA, MACD, RSI, and other indicator types are optional.
- Simulated trading and accounting. Apply the SMA crossover strategy in a simulated account. Track orders and fills, cash, positions, and realized and unrealized profit or loss. Make the account state and trade history understandable, and document the assumptions used to simulate execution and calculate results.
- Backtesting. Evaluate the strategy on historical data using only information available at each decision time. Show the resulting trades and account performance, and explain what the results establish and what they leave uncertain.
Verify the moving averages and crossover against a trusted reference, compare batch and incremental calculations, and explain how unfinished candles are handled. Check simulated accounting against known examples. Keep browser tests and run automated checks on pushes using GitHub Actions.
Outcome: an integrated AI-assisted trading bot with text, vision, and live audio.
- Decision API. Build an application endpoint that asks an AI model for a trading decision, such as buy, sell, or hold. Supply relevant market observations, indicators, and simulated-account context. Explain the information sent, the response received, and the application checks applied before the response can cause a simulated action.
- Automated trading bot. Connect the decision API to the trading simulation so that the application can act on checked decisions automatically. Explain how the SMA crossover and AI decision work together. Show the decision, its explanation, the action taken or skipped, and the resulting account state.
- AI-assisted interaction. Include a chatbot grounded in the workstation’s data and simulated activity, a vision-language model that receives and interprets chart imagery, and two-way real-time speech through a live API. These capabilities are required; students may choose whether they share a provider or model. Explain the context each receives and how its response helps the user understand the workstation.
Demonstrate the complete path from market data and indicators to a checked model decision and simulated outcome. Test invalid model responses, unavailable services, and audio-session failure; distinguish mocked checks from live-provider observations. Demonstrate the live model and audio integrations. Update the project documents, verify a clean checkout, and record the demonstration and process screencast. All trading must remain simulated.
Students will present the working application in class during the final week of classes. Trace an example from the chart and indicators through an AI-assisted decision to a simulated trade or hold and its account outcome. Demonstrate the chatbot and the roles of vision and live audio, and explain a backtesting result. Discuss an important design decision and a verification result, and identify mocked, unavailable, or unfinished behavior. Each student completes only the presentation item assigned to them in Canvas. The recorded demonstration and process screencast remain part of the Part 4.3 submission.
- [Final Presentation — Part 1](https://psu.instructure.com/courses/2484533/assignments/18824047): Tuesday, December 8, 2026.
- [Final Presentation — Part 2](https://psu.instructure.com/courses/2484533/assignments/18824053): Thursday, December 10, 2026.
Both sessions meet from 1:35 to 2:50 PM Eastern in Westgate E202. Students must present during their assigned session. No makeup or overflow presentation session is scheduled.
For each of Parts 4.1, 4.2, and 4.3, upload only report.md to the corresponding Canvas submission page. Each report must include:
- Report. Summarize what was completed, key design decisions, verification results, and remaining limitations. Include links to supporting documents and evidence.
- GitHub repository. Include the repository URL and the commit identifying the submitted version.
- Short video. Include an accessible link to one video lasting 30 seconds to 1 minute, demonstrating the working application features required for that part.
Do not upload source-code files or ZIP archives to Canvas. Keep source code in the linked GitHub repository. Ensure that the instructor can access both the repository and the video.

These submission requirements apply to the three project parts. The in-class presentation does not require an additional upload.
- [\[Assignment 4.1\] Part 1 — Submission](https://psu.instructure.com/courses/2484533/assignments/18507002): market data and the dashboard.
- [\[Assignment 4.2\] Part 2 — Submission](https://psu.instructure.com/courses/2484533/assignments/18507004): indicators, simulated trading, and backtesting.
- [\[Assignment 4.3\] Part 3 — Submission](https://psu.instructure.com/courses/2484533/assignments/18674774): AI-assisted automated trading and interaction.
Consult each Canvas submission page for its current due date.

The final submission includes:
1. The GitHub repository, linked in report.md and verified from a clean checkout, with a docs/ folder describing the system that exists rather than the one that was planned.
2. The demonstration video and process screencast. Submit one combined video lasting 30 seconds to 1 minute. Show the integrated application in use and briefly identify one design or verification decision. In the report and evidence log, explain one failure or revised approach, the evidence used to understand it, the resulting decision, and a relevant piece of generated code. No separate process recording is required.
3. A tool-and-model disclosure. Which coding agents, editors, and models were used, what each was used for, and where that choice changed during the assignment and why. Record this in AI-USE.md, continuing the course disclosure practice. Disclosed use is expected and carries no penalty; undisclosed use is an academic-integrity matter.
4. A curated, redacted evidence log whose selected entries connect the intended change or question, the relevant prompt or instruction excerpt, the resulting file, diff, or commit, a test or browser observation, the decision taken, and any remaining uncertainty. Include at least one failed or revised approach. Redact credentials, personal information, and private third-party content; a complete chat export is neither required nor desired.
The three project submissions and the in-class presentation are each graded out of 100 and carry equal weight within the Assignment 4 group. The criteria apply to the work expected at each stage; they do not create additional graded items.
1. Functionality and integration — the required behavior for the submitted part works in the running application. The completed workstation connects live data, indicators, simulated trading and backtesting, the decision API, chatbot, vision, and audio.
2. Code comprehension and ownership — students can explain relevant generated code and trace data from its source through calculation, model context, decision checks, and simulated accounting.
3. Specification and process — current design documents, the process screencast, and the curated evidence log explain decisions, verification, and revisions during development.
4. Domain responsibility (correctness) — recorded observations, replay, indicators, model decisions, and simulated outcomes are supported by the evidence available at the relevant time.
5. Testability and reproducibility — the system can be exercised without a live market, automated checks support the claimed behavior, and the README supports a clean checkout.
6. Design and user experience — charts, derived signals, AI explanations, and account results are readable and connected. The interface makes simulation status, data age, and failures clear.
Assessment emphasizes the connections between components and the ability to explain and verify them. A positive simulated return is not a grading requirement. The live presentation should make the integrated behavior and its limitations understandable to the class.

[← Return to Module VII — Assignment 4: Live Market Workstation](https://psu.instructure.com/courses/2484533/modules#context_module_6139771)