# ChatbotX extension verification — 6 November 2026

## Local implementation evidence

* Existing Python suite: 656 tests, 655 passed and one Windows/POSIX-specific skip. No failures.
* Nine new adoption tests: passed. They cover DST gap/overlap behavior, holidays/weekends, immutable SLA snapshots, simulated/draft exclusion, accepted replies during human hold, tenant isolation, OAuth PKCE/cookie/state/replay checks, encrypted Google grants, atomic consent-safe contact import, uncertain append deduplication, booking overlap/reconciliation, semantic spending gates, source filters and stale-index rejection.
* Thirty affected adoption/deployment/source-initializer/PDF checks: passed after the final runtime changes.
* Existing 27 JavaScript suites: passed after loading the new module in the smoke harness. The all-routes suite renders 31 destinations from an isolated Store state.
* New extension UI contract suite: passed for empty/setup-disabled states, real action controls, escaping and stale-workspace response rejection.
* Python compilation, JS syntax, UTF-8 checks and Git whitespace checks: passed.
* `tzdata` is hash-pinned as a runtime dependency; source initialization probes Asia/Kolkata and America/New_York before release activation.

## Browser evidence and limits

REA captured the isolated mobile launch/login surface at 390×844. The subsequent authenticated scenario timed out at the host after 450 seconds without returning evidence. No remaining owned headless Chrome process was observed afterward. This is not a successful authenticated visual check. No real customer records, credentials or paid providers were used in the isolated QA workspace.

## Provider limits

Google Cloud OAuth credentials are not configured yet. Google OAuth/import/export/booking contracts passed against controlled responses, but live Google acceptance remains pending. Semantic retrieval is off by default; there were no OpenAI inference/embedding calls. Existing Meta real-usage settings remain intact; there were no test messages, calls, charges, shipments or recovery-email sends.

This release does not establish full WATI parity, Google public-app approval, Meta Tech Provider approval or end-to-end calling/commerce acceptance. The new gateway repositories were researched only; they are not silently installed.

## Deployment

Release pin, Hostinger action, container health and deployed asset checks are recorded after rollout below.
