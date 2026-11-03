# Background agents and OpenAI connection

Updated 29 October 2026. Exact WATI parity remains the target and is **not achieved**. The machine-readable acceptance ledger is [wati-ai-parity-checklist.json](wati-ai-parity-checklist.json). Backend request contracts, UI renderer checks and browser/provider verification are different evidence.

## Implemented

- All eleven REA-observed agent role presets plus Daily Digest. Each saves independently written instructions in its own business workspace.
- Agent editing, archive/restore, on-demand analysis, persistent hourly/daily/weekly schedules, pause/resume, next-run and last-outcome display, activity/run history and pending findings review.
- A dedicated agent worker runs separately from the outbound message worker while the local server is running. Due times advance before execution. Missed intervals are skipped rather than replayed after downtime.
- SQLite execution leases prevent overlapping manual/scheduled runs of an agent across processes. Lost leases cannot publish findings. Archiving revokes leases; restoring cannot revive an old in-flight run. Pausing a schedule affects future runs, not an already-started model request.
- Background runs only create proposals. The model cannot send messages or execute arbitrary tools. The existing administrator review flow controls allowed local mutations.
- Ask/Agents navigation, private recent chats, Daily Digest access, panel expand/restore, navigation collapse, context-chip dismissal, Ask/Summary/Draft/Analysis modes, selected-conversation scope and archived-agent controls. The observed WATI mode choices and creation form remain unverified; these implementations are not asserted to be identical.
- Pending answers cannot overwrite a newly selected chat. Chats retain their selected agent identity. Inbox selection is applied before the twenty-contact sampling limit.
- Provider choice: local Ollama or OpenAI Responses API. OpenAI uses a fixed official HTTPS endpoint, structured JSON Schema for findings, no provider tools, no automatic retries and `store:false`. Refusals, incomplete responses and malformed findings produce explicit failures.
- Workspace-specific paid-call approval gates prevent enabling one business from enabling paid calls for another. Keys are server-only; workspace keys can override the server key. Status and prompts never contain API keys.

## Configure locally

1. Open the local app and create its owner account. An existing WATI login does not create an account in this separate application.
2. Edit `.env` beside `server.py`. Keep it out of chat, Git and shared ZIPs. The template has been prepared without credentials and with live/paid operations disabled.
3. For OpenAI set `TW_AI_PROVIDER=openai`, `TW_AI_MODEL=gpt-6-luna` (or the model you choose) and `TW_OPENAI_API_KEY` locally. The key may instead be scoped with `TW_AI_<UPPERCASE_WORKSPACE_ID>_OPENAI_API_KEY`.
4. After explicitly approving paid usage, set both `TW_AI_ENABLED=true` and `TW_AI_<UPPERCASE_WORKSPACE_ID>_ALLOW_PAID=true`. These are not enabled during preparation. Restart the server after editing the file. Settings displays the workspace's exact variable prefix.
5. Begin with one manually requested analysis. Review evidence and output quality before enabling schedules. The app cannot establish WATI-equivalent AI quality from a passing transport test.
6. Meta uses its own workspace credentials and live gate described in CONNECTIONS.md. Ordinary phone numbers and Meta Business login alone do not substitute for Cloud API IDs/tokens and a reachable signed webhook.

The starting model recommendation is GPT-6 Luna for focused high-volume analysis, with GPT-6.1 Sol available as a separately chosen higher-cost model for complex tasks. No automatic model escalation is implemented. Availability and suitability must be checked with the user's account and evaluated with representative cases. Official sources: [OpenAI models](https://developers.openai.com/api/docs/models), [Responses text generation](https://developers.openai.com/api/docs/guides/text), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Ollama chat API](https://docs.ollama.com/api/chat).

## Verified and remaining

66 Python tests passed. Python compilation, all JS syntax checks, UI renderer checks and asynchronous chat-race checks passed. Independent reviews found and rechecked fixes for selected-contact sampling, archive/restore fencing and stale chat responses. OpenAI tests used controlled transport responses, and scheduler tests used temporary databases and controlled model output. No paid/provider calls, template submissions, WATI activation, purchases or customer messages were made during verification.

REA passively reconfirmed the expanded catalog as `ev_a8293f84de1b521d773350942e4e364dbbb296ba0893d28f37a6f42a394d11c0`. The screenshot request timed out after 30 seconds. WATI's private backend, exact agent configuration/scheduling/review screens, current pixel-level parity, production operations and real OpenAI/Meta behavior remain unverified. Local Ollama was not reachable.

Commerce, media/calls, broader integration adapters, full automation parity, public client onboarding and production hosting/billing remain incomplete. This release does not make the entire WATI clone complete.
