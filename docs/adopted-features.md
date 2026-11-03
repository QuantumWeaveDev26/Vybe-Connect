# Feature adoption release

## Adopted feature update — 29 October 2026

This update implements working parts of the requested WATI/competitor feature set. Full WATI parity and production readiness remain incomplete.

- **Sales pipeline:** persistent contact-linked opportunities, New/Qualified/Proposal/Won/Lost stages, team owner, validated integer minor-unit amounts and separate currency totals. Values are team-entered estimates, not payment receipts or attributed revenue. Deal contact changes are blocked while linked follow-up tasks exist.
- **Follow-up tasks:** contact/deal links, owner, optional timezone-aware due date, overdue display, complete/reopen and editing. Tasks do not trigger automatic WhatsApp messages or notifications.
- **AI findings:** saved-agent on-demand analysis, persistent run history and pending findings with supplied message references. The local model receives the existing bounded workspace context and must return strict structured JSON. Unsupported actions, invented references and malformed output cause an explicit failed run; no canned findings are supplied.
- **Human review:** admins may dismiss, acknowledge, or apply one allowed local proposal: add tag, assign to a human, add internal note, create reply draft or create follow-up task. No sending, payment, arbitrary HTTP/API request, blocking or deletion action is available. Each finding is applied at most once inside a transaction and audited.
- **Stale protection:** model context and proposal fingerprints derive from one database read snapshot. Changed contacts/messages or findings older than 24 hours cannot be applied. Applying a proposal to a contact invalidates other findings for that same contact; run a fresh analysis for further changes.
- **Human takeover:** the inbox offers Take over / Resume automation. Takeover assigns the chat to the operator and pauses keyword/graph processing. Graph handoff and approved agent assignment also hold the conversation. Incoming messages and STOP consent processing continue. Resume explicitly resets any previous flow session. Campaigns are managed separately.

Verification: **50 Python tests passed**, including HTTP persistence/assets and both independent-review regressions. Python compilation, all JavaScript syntax checks and Node UI renderer smoke checks passed. The latter cover pipeline/findings rendering, escaping, role visibility and inbox takeover controls, not real-browser visual appearance. Independent code review found a stale-context race and linked-task contact inconsistency; both were fixed and rechecked with no remaining findings within that review scope.

REA re-observation: `ev_fe6458037ca09f1682210a0bc5fc3348a75c3b9a5c32402156697ead8505fd10` confirms the observed eleven-agent catalog. No WATI Hire, Send, activation or settings changes were made. No paid APIs or real provider calls were used in verification. Real Ollama answer quality, Meta delivery and latest visual parity remain unverified.

Still pending: scheduled/background agents, richer findings/actions, customer-facing AI execution, broader workflow triggers, round-robin/availability routing, commerce/store/payment adapters, omnichannel support, production onboarding/billing/hosting and the rest of PARITY.md. This update does not make the entire WATI clone complete.
