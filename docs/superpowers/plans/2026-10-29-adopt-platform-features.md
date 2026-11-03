# Adopt CRM and reviewed AI actions implementation plan

> Execute inline with the executing-plans skill, one testable task at a time. User has authorized implementation and opted out of further design questions. Full WATI parity remains the overall objective; this is a bounded implementation increment.

## Specification

Use the authenticated REA agent catalog and review-first descriptions as evidence, including `ev_fe6458037ca09f1682210a0bc5fc3348a75c3b9a5c32402156697ead8505fd10`. Adopt the researched competitor features as requested. Preserve all existing inbox, contacts, campaign and provider behavior. No paid APIs, customer sends, external account changes or deployment during development.

Files: `crm.py` for deal/task domain validation, `reviews.py` for model findings validation and reviewed local actions; `store.py` for scoped persistence and transaction integration; `static/business.js` and `business.css` for pipeline/tasks and agent findings UI; existing shell/app/server for routing/assets; focused tests and release docs.

- [x] Task 1: failing domain tests, then persistent contact-linked deals (stages, currency-safe integer amounts, owner), follow-up tasks (due time, owner, completion), workspace/member/role validation. Add pipeline and task UI using real saved records. Check boundaries and persistence.
- [x] Task 2: failing tests, then on-demand structured AI runs. Reuse current bounded workspace context and configured local model. Strictly validate finding schema and contact references. Persist runs and pending findings; no side effects from analysis. Admin review can dismiss or apply only tag, assignment, internal note, draft reply or task creation. Apply atomically once, reject stale targets, no message sending or arbitrary tools. Add run history and findings review UI. Prove invalid/foreign IDs and duplicate approvals cannot change records.
- [x] Task 3: human handoff/takeover UI using recorded contact assignment/status, with an explicit persistent hold flag that stops keyword/graph automation after takeover. Prove inbound storage continues but automation pauses until explicitly resumed. No autonomous agent is claimed.
- [x] Task 4: full regression suite, Python/JS syntax, local HTTP assets, manual code review, update parity/connection docs and clean source ZIP. Current visual/live-model/live-Meta verification remains explicitly pending.

Decision: keep CRM actions available to agents, consistent with current contact/inbox access. Only admins apply AI-proposed mutations. Model calls occur outside SQLite transactions. No new paid provider or package installation. Financial deal values are user-entered estimates, not payment receipts or revenue attribution.

Execution ledger: all four scoped tasks completed and verified locally. Full suite 50 passed; UI renderer smoke checks passed. Independent review found and rechecked two corrected defects. Ruling: freeze proposals against the captured database read snapshot to prevent accepting context that changed before the model request; reject deal-contact changes with linked tasks rather than silently moving tasks between customers. Visual/live-provider acceptance remains pending.
