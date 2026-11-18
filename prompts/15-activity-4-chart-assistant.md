# Activity 4 — Chart assistant (supplied November 17, 2026)

Source: student-supplied Canvas page text and screenshot, “Building an Agent in the Trading App.” User request: “implement this agent according these prompt into my workstation, but fit my Ui/UX”. This file preserves the implementation requirements from the supplied prompts; the complete course page remains on Canvas.

## Setup

Prepare the existing backend environment for openai-agents==0.24.0 and openai==3.52.0. CHECK the interpreter, packages and pip check. TAKE ACTION only after showing the exact command, target and affected dependencies and obtaining student approval. VERIFY AsyncOpenAI, Agent, Runner, function_tool imports, versions and pip check. Do not create a new environment or update unrelated packages. Student approved the proposed installation and websockets change in this chat.

## Connect tools

Add a read-only agent using Agents SDK. Reuse rule lookup and chart Decision API functions, expose them as function tools and register them. Rule lookup should explain current definitions; chart assessment should request a new decision on the captured chart. Capture the chart in the browser and bind it to the request. Keep credentials on the backend. Return actual tool results including errors. Verify schemas before adding chat. Identify checks that still need a real API call.

## Chat interface

Add chat fitted to the current UI. Capture the chart on Send. An ambiguous “Should I wait?” should ask whether the user wants a definition or an assessment. Show reply and expandable tools/results. Report ticker, chart time, choice and probability when available. Use the same tool result for chat/chart result/marker. A delayed result for a different chart must not appear on the current chart. Rule explanation alone must not assess. Verify rule question, assessment and failure; leave trading actions outside this task.

## Follow-up context

Compare a new assessment with an earlier assessment of the same ticker and data mode in the same conversation. Preserve previous tool result and chart time. Say if none exists. Add New chat. Test in one conversation:
1. What does WAIT mean in this app?
2. Run the decision on the chart I'm looking at. What do you recommend?
3. After a later chart snapshot: Run a new decision for this chart and compare it with the earlier assessment.

Verify tools used, exact returned choices/probabilities, both chart times, and updated marker. Save screenshots and record mismatches. Example conditions: LONG when the last two completed candles each close above their own open; SHORT when both close below their own open; WAIT for mixed, flat, insufficient, unclear or stale evidence. Probability is choice confidence, not probability of a profitable trade.
