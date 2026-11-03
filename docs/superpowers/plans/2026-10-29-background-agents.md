# WATI-style background agent increment

User priority: Wati AI and all observed agents, not merely visual cards. Use existing REA evidence for the eleven-role catalog and review-first findings. Exact WATI scheduling/configuration behavior and private backend are not established; implement an independent durable scheduler and state its boundaries.

- [x] Add failing scheduler/lifecycle tests. Implement persistent agent configuration (edit, archive, schedule enable/pause and hourly/daily/weekly intervals), workspace/admin boundaries, explicit model configuration prerequisite and per-agent execution leases.
- [x] Implement a dedicated background worker separate from outbound messaging. Persist due times before execution, skip missed intervals after downtime, prevent overlapping scheduled/manual runs, fence stale leases and recover interrupted runs. Background AI only creates reviewable findings; no customer messages or automatic mutations.
- [x] Add agent management UI inside AI panel: saved agents, editing, pause/resume schedule, next run, last outcome, run-now and findings links. Fix panel state when opening Agents for the first time. Keep catalog and knowledge controls. Add agent configuration to model diagnostics.
- [x] Verify all regressions, scheduler concurrency/restart/failure boundaries, JS renderers and HTTP. Independently review, document precise scope, restart local build and refresh clean source ZIP.

No paid calls, model downloads or provider account changes without existing authorization. Live AI verification requires an available configured runtime. Worker runs only while the local server is running; hosting/service management is separate. Commerce, media/calls, onboarding and broader integrations remain part of the overall backlog, not silently treated as delivered by this increment.

Execution ledger: scoped increment implemented, independently reviewed and regression-tested (66 Python tests, syntax/renderer/chat-race checks). Added the user-selected OpenAI provider after official documentation review. All live/paid flags remain disabled. Selected-contact sampling and archive/restore fencing defects were fixed and rechecked. Live-provider tests require local owner/credentials setup and explicit paid-call approval. Full exact WATI parity remains incomplete.
