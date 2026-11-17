# Operations and AI verification — 17 November 2026

This release extends the existing team, calling and analytics modules. It does not add customer pages or activate providers.

- Per-agent calling, report and export permissions are checked against current membership at request time. Administrators retain full access; existing agents retain their previous access until configured. Removing a member also removes their capability policy.
- Ringing calls can be assigned to an eligible teammate with an ownership fence. Busy members cannot claim another call. Internal call notes and paginated, workspace-scoped history work without Meta. Active-call media transfer and recording are not implemented.
- Reports include recorded reply cycles, manual conversation resolutions, server-observed call durations and operator activity, including former members. CSV generation is server-authorized and protects spreadsheet cells from formula injection. Missing historical timestamps are not reconstructed; automated replies count as replies, while resolution events cover manual status changes.
- Customer AI context now selects recent eligible messages within an 8,000-character budget, excluding private notes and unverified outbound drafts. Saved-reply personalization supports CRM attributes and canonical placeholders without recursive interpolation; applying it creates an unsent draft.
- Updated script fingerprints prevent stale cached versions of the changed UI modules.

## Evidence

The final full regression run passed 747 tests with one Windows-only skip (POSIX secret-file permissions). All 34 JavaScript suites passed. Focused latest checks passed: operations 15 (including invalid and oversized history cursors), growth services 29, repository adaptations 3, customer assistant 22, analytics 8, and HTTP operations 3.

An explicitly approved synthetic live OpenAI smoke test submitted two requests: Daily Digest and a grounded customer-reply draft. Both completed; conservative cost upper bound was US$0.003589 against the approved US$0.02 maximum, with no unresolved cost reservations. No Meta messages, charges, production customer records or outbound sends were involved. This proves those two model workflows, not every agent or the production tenant's credentials.

Local browser checks verified report timings, mobile permission persistence, internal-note persistence after reload, history completion and refreshed asset loading using an isolated synthetic workspace. Live provider calling/audio, Meta customer onboarding, Razorpay subscription acceptance, Google OAuth and recovery-email delivery require separate provider readiness and acceptance. Full WATI/Emovur equivalence is not claimed.
