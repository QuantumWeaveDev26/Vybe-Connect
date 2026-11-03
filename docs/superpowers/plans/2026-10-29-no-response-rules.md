# Customer no-response rule implementation plan

Continue inline with TDD during the authorized hour ending 12:01:55 UTC. Add a no-response trigger using actual accepted outbound messages, never drafts or uncertain sends. Wait 1 second–7 days from recorded acceptance. Rule saves establish a message-ordinal watermark, so enabling/editing cannot replay historical conversations. Persist the latest accepted anchor on the contact and one evaluation record per rule/anchor.

A later real inbound, STOP, human takeover or human handoff prevents continuation. Simulations do not cancel a real watch. Each due rule evaluates once against current segments/dependencies and executes only the existing bounded local actions; it never sends a follow-up itself. Use one transaction and unique identity for competing workers. Chained/repeated messages rearm only after a new actual accepted outbound. Current manual text, queued templates, customer AI and media acceptance paths must record anchors; delivery/read upgrades must not reset the wait.

- [x] Add failing timing/restart/replay, source eligibility, configuration watermark and control tests.
- [x] Implement acceptance tracking and transactional due evaluation with sender hooks.
- [x] Add no-response duration controls and evaluation history.
- [x] Run checks, document limits, package and restart, then continue remaining scope.

Verification: 309 Python tests passed in 110.720 seconds, targeted mocked sender assertions passed, Node renderer and JavaScript syntax checks passed. Local server restarted on 8788; HTTP root and new rule controls returned 200. Source package refreshed after documentation. Exact WATI/live provider verification remains unfinished.
