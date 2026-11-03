# Owned catalogue and customer orders

Commerce now has four sections: Your catalogue, Customer orders, Activity and Shopify connection. The existing read-only Shopify connector remains separate. These workspace-owned records are real persisted business records after owner sign-in, not simulated provider transactions.

Administrators can create and edit products with a unique SKU, a supported two-decimal currency, an exact unit price, availability and stock. Updates require the current record version. A product is made unavailable rather than deleted, retaining historical order references.

Orders select a current workspace contact and 1–50 unique product lines in one currency. Drafts snapshot names, SKUs and prices; saving an edited draft refreshes those snapshots. Drafts do not reserve stock. Confirmation checks current product availability and stock and deducts all lines in one SQLite transaction. A failed line rolls the whole transaction back. Concurrent confirmations cannot oversell. Confirmation also increments product versions so a stale product editor cannot overwrite its stock change.

An order can move from draft to confirmed or cancelled, and from confirmed to fulfilled or cancelled. Cancellation of a confirmed order restores stock. Fulfilled and cancelled orders are terminal. Repeated submissions of the same current status return the current record without changing inventory again. Other stale transitions are rejected. Every actual mutation creates a versioned commerce event and a workspace audit entry.

These workflows do not charge customers, issue refunds, book shipping, calculate taxes/discounts, publish a Meta catalogue or mutate Shopify. Fulfilment is a team-recorded status. Those integrations remain separate unfinished work, and this release does not claim complete WATI commerce parity.

Public review contains one clearly labelled example product and draft order in its isolated sample store. Public review still cannot save changes. Real owner data is not exposed or copied into the review store.

Validation on 3 November 2026:

- Full suite: 494 Python tests passed in 237.724 seconds.
- Focused checks cover concurrent confirmations, atomic rollback, idempotent cancellation, stale versions, input validation, terminal states, roles and workspace isolation.
- Node renderer/privacy tests pass, including escaped product names and administrator-only controls.
- Browser lifecycle in a disposable authenticated QA workspace: create a contact and product; save a two-unit order at ₹125.50 each; confirm the ₹251.00 order and observe stock 5 → 3; cancel and observe stock 3 → 5; inspect the persisted activity entries. No browser console errors were observed.
- Template sync and submit controls now remain disabled while Meta is disconnected or public review is active.

Calling, subscriptions/billing, public client onboarding, full knowledge/automation parity, live provider acceptance, complete visual equality and operational clearance remain unfinished. Adding environment variables alone does not implement these missing features.
