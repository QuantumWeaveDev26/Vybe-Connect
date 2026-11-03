# Persistent chatbot wait implementation plan

Continue inline with TDD. Add a bounded wait node (1 second to 7 days) to the existing acyclic draft-producing graph. Contact sessions persist due time and flow version. A timer worker advances one due contact transactionally; duplicate workers cannot produce duplicate continuation drafts. Each subsequent wait starts from actual continuation time.

Incoming messages while waiting are recorded but do not skip the delay or become a future question answer. STOP and human takeover cancel the active session. Any saved flow edit/disable cancels its existing sessions; snapshot-version preservation and publishing remain pending. Timer continuation only creates drafts and local graph updates, never a paid call or WhatsApp send.

- [x] Write failing delay, restart, duplicate worker, inbound, edit, STOP and takeover tests.
- [x] Implement wait validation, versioned sessions, timer processing and cancellation.
- [x] Add visual wait editing, timing details and active-wait status.
- [x] Run regression, update parity scope, package and restart. Continue through remaining gaps afterward.
