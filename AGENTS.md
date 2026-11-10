# Project instructions

- Preserve Vue, FastAPI, SQLite, localhost operation, and Yahoo live streaming.
- All trading must remain simulated. Never claim mocked or replayed data is live.
- Keep source timestamps separate from receipt times and show source age.
- Persist revisions; avoid silently overwriting recorded evidence.
- Verify duplicate, revised, out-of-order, and replay behavior when modifying ingestion.
- Run `python -m pytest backend -q` and `npm.cmd run build` in frontend after relevant changes.
- Keep README, docs, AI-USE.md, and evidence accurate; do not invent videos, provider observations, or results.
- Never commit credentials, local databases, dependency folders, or private content.
- Work inside this project root, inspect relevant files before editing, preserve existing work, and show the change summary for student review before a commit.
- Preserve the student's terminal UI layout, dark palette, watchlist, and chart/sidebar structure when adding controls.
- Save major supplied prompts under prompts/ and observed results under docs/verification.md. Keep later-stage prompts as reference until that stage is authorized.
- Before adding a tool or dependency: CHECK the OS, runtime, existing environment, manifests and lockfiles; TAKE ACTION by explaining purpose, compatible version, exact command, target and affected files and obtaining student approval; VERIFY the smallest import/version/build check and record expected/observed results. Reuse the existing Python environment; do not create a new one by default.
- SmokeTest is `.venv\Scripts\python scripts/smoke_test.py` on Windows, or `python scripts/smoke_test.py` in the selected Python environment. It starts isolated backend/frontend services, opens the real browser, exercises Part 1 UI/API/database operations using labeled fixtures, checks proxy failure/recovery and persisted records, and cleans up. It does not edit source or install dependencies. Live Yahoo checks remain separate.
- AutoLoop means inspect a failed check, make the smallest in-scope correction, and rerun it. Stop on success, after five correction cycles, or when further permission is needed. Record failures as well as passes.
- At handoff follow handoffs/create-handoff.md and update handoffs/current.md.
