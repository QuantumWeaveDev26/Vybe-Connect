# Internal team access and mobile workflow

**Goal:** QuantumWeave AI is subscription-free for its own invited team; customer workspaces remain subscription-gated. Preserve existing CRM, inbox, sales, automation, knowledge, commerce and reporting modules.

**Design:** A private exact-ID allowlist identifies internal workspaces. This is not a public role, browser flag or exemption inherited by another workspace. Internal CRM access is separate from a paid subscription and does not bypass member permissions. Provider charges remain separately gated. Internal AI is paused by default; an explicitly enabled, bounded monthly allowance can be configured later without inventing a paid subscription.

**Target:** Only existing production workspace QuantumWeave AI (`eaa91c5fe6f20007`). No exemption for customer, demo or QA workspaces.

**Mobile:** Preserve the mint theme. Synchronize menu button state, support drawer focus/Escape and backdrop dismissal, use comfortable header targets, and verify portrait/landscape plus tablet and laptop layouts. No new customer pages.

- [ ] Write failing access tests: team vs customer, no user-supplied bypass, checkout prevention, provider calls paused, bounded optional AI allocation.
- [ ] Implement `internal_access.py`; integrate CRM enforcement, service state, AI entitlements/reservations and checkout guard.
- [ ] Update existing billing/AI summaries for internal use; keep paid customer cards unchanged.
- [ ] Test and fix mobile navigation and header targets using isolated browser previews.
- [ ] Run unpaid regression and review changes; commit/push if GitHub access permits.
- [ ] Deploy source while preserving keys/data and set only the approved exact internal workspace ID. No paid provider calls or automatic-send activation.
- [ ] Verify original production site and internal/customer boundaries; report external acceptance honestly.
