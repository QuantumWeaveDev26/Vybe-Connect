# Natural-language agent creation implementation plan

Continue inline using executing-plans and test-driven development. Existing scope and the user's repeated instruction to proceed supply the implementation direction; no new design approval is needed.

Design: Create an agent opens a private builder conversation. A genuine configured AI provider generates a structured, editable agent proposal through the existing durable job queue. Generation never installs, schedules or runs an agent. An administrator reviews the instructions and suggested interval, then explicitly installs a review-first agent with scheduling disabled. Proposal installation is atomic and idempotent. Other users/workspaces cannot read or apply it. Provider activation and paid-call gates remain unchanged. This is independent behavior implementing the observed WATI entry point; exact WATI internal creation behavior is not established.

- [x] Add failing tests for structured generation, schema rejection, role boundaries, private ownership and idempotent installation.
- [x] Implement agent_builder.py for bounded proposal schema, parsing and transactional installation; extend openai_background.py with strict structured output.
- [x] Extend chat_jobs.py to preserve builder purpose, revalidate authorization at execution/application, retain cancellation and publish proposals without side effects. Support configured Ollama JSON output as well as OpenAI.
- [x] Add builder chat entry, editable proposal review, paused installation and renderer checks to assistant.js.
- [x] Run focused then full local checks, update parity ledger and ZIP, restart the local server and probe release assets. Do not invoke live/paid providers during checks.

Verification: 127 Python tests pass, including 11 agent-builder tests. JavaScript syntax, Python compilation and renderer/privacy checks pass. No live or paid providers were invoked. Independent final review and visual browser acceptance remain unavailable; no further parallel workers were started after the prior credit limit.
