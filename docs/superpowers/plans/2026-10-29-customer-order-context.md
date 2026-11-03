# Customer order context implementation plan

Continue inline using the existing Python/SQLite architecture. The user has already requested implementation without further design questions. Use TDD and local provider doubles.

Design: administrators explicitly verify and link a synced Shopify order to a workspace contact. No order-number guessing, phone matching, extra customer-data ingestion or automatic provider reads. Assistant order access is separately opt-in, false by default. Only linked orders from the currently configured shop, synced within 24 hours, enter bounded selected-customer context with a last-sync timestamp. Stale/missing records require human help. Order/link changes fence pending model results. No payment, fulfillment or order mutations.

- [x] Test role/tenant scope, explicit ownership confirmation, linking/unlinking, default-denied access, bounded fresh context and stale-result suppression.
- [x] Implement order link actions, projected context, assistant opt-in and fingerprint coverage.
- [x] Add commerce link review and assistant configuration controls.
- [x] Run regression, update documentation, package source and restart the local app. No live paid/provider operations.
