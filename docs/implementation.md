# TeamWave implementation contract

User authorized immediate implementation after inspecting WATI. Build an independently owned application with WATI-style workflow organization for internal use and future client services. This release is a local pilot, not complete WATI parity or a publicly deployable SaaS.

## Architecture and tasks
Python 3.13 standard library HTTP server and SQLite, browser HTML/CSS/JS. No package installation or external services required. Workspaces isolate all records. Passwords use PBKDF2; sessions use opaque random tokens. Admin and agent permissions apply at the service boundary. Bind to 127.0.0.1. Reject cross-origin browser writes and invalid Host headers. No paid calls in development.

1. Write regression tests for tenant isolation, authentication, permissions, CSV errors, opt-in campaign targeting, webhook deduplication, keyword drafts, service windows and safe export. Observe failures before implementing.
2. Implement store.py (persistent domain), server.py (HTTP boundary), meta.py (official adapter with disabled-by-default sending). Tests run with python -m unittest discover -s tests -v.
3. Implement static app with campaign overview/calendar, inbox/notes/assignment, contacts/segments/import/export, template drafts and preview, campaign draft/demo execution, rules, visual local conversation graphs, reusable replies, sequence definitions, analytics, team/workspaces and connection diagnostics.
4. Verify local HTTP/security boundaries and UI in browser; package clean source ZIP and launch local preview.

## Limits and remaining parity
Template submission/sync, a persistent outbound queue and a local AI adapter are implemented; real-provider verification remains pending. Media, Meta Flow publishing, broader automation, commerce, ads, public onboarding/billing, production hosting and hardening remain pending. Local template/demo statuses are never presented as Meta approvals or real delivery/read receipts. Sequences/visual flows are local configurations with explicit runtime scope. No WATI scripts or private customer data are distributed with the source.

## Evidence
REA authenticated capture ev_f9283082f2b07f3cbe4c83f1b966d9ba25ccce6472cdb6e90808e6bc08a740fa. REA script export ev_b4c2ba1addb1a24af7eeae0ead3a39991da6bfdae920742b0473a1b51f32dbcf retained 281 script records. Focused static analysis was partial due to a 30-second source timeout; it does not establish complete routes or backend behavior. Browser UI inspection established additional navigation/screens described in PARITY.md.

## Final execution ledger
- Latest full suite: 35 tests passed, including tenant-scoped business knowledge sources (29 October 2026).
- Added flows.py for bounded graph execution and static/graph.js + graph.css for the visual editor.
- Browser QA and syntax/compilation checks completed; see VERIFICATION.md.
- Campaigns use a durable SQLite outbound queue when the per-workspace live gate and approved template requirements are satisfied. Sandbox simulations remain explicitly opt-in. Graph replies remain drafts. No live provider calls were made during verification.
- Production readiness and full WATI parity remain explicitly incomplete.
