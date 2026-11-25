# Live AI acceptance — 25 November 2026

## Deployed behavior

Both approved internal workspaces, **bmai** and **QuantumWeave AI**, share one INR 299 monthly AI ceiling and one request allowance. Existing monthly reservations were retained. Concurrent requests reserve against the combined total before a paid request is submitted; changing the workspace allowlist does not erase prior reservations. Customer workspaces retain their subscription gates.

The live retest reproduced database contention behind an indefinitely waiting Ask request. Write-ahead logging now allows workspace snapshots and worker/budget commits to coexist. The concurrency regression, atomic two-workspace budget tests and production database integrity checks pass.

## Actual Chrome acceptance on the deployed website

- bmai's Ask interface submitted a real OpenAI request, displayed processing progress, then displayed **READY**. Saved history reopened the same answer without another paid request.
- All 12 preset agents were saved in bmai as on-demand agents and each completed one live run through its **Run now** button: Daily Digest, Inbox Triage, Re-engagement Scout, Urgency Watcher, Top Topics, Spam Watcher, Ready-to-Buy, Automation Health Check, Campaign Readiness Checker, Segment & Contact Checker, Campaign Idea Finder and Account Health Checker.
- Results used the actual empty bmai workspace and correctly disclosed missing conversations and campaign evidence. No sample customers or invented performance metrics were inserted.
- Schedules remained disabled. Findings are proposals for human review; none were applied. No Meta requests, external messages, payments or shipping operations were triggered.
- The shared ledger after acceptance held **INR 137.49 in conservative reservations**, leaving **INR 161.51** from the approved INR 299 ceiling. Reservations are safety bounds, not the OpenAI invoice. Earlier failed/uncertain requests were not refunded or automatically retried.
- Mobile AI, navigation, inbox, team and billing screens were checked at 320, 390, 768, 1366 and 1920 CSS pixels. The duplicate mobile inbox empty pane was removed after this check.

## Teammate use

Invite teammates into **bmai** or **QuantumWeave AI** from Team management. They should accept their invitation using their own account rather than create an unrelated customer workspace. A regression check verifies a regular invited member can start private AI chats and run saved agents while remaining unable to configure agents.

The unpaid full suite passed 776 checks with one skip before the additional member regression; the updated internal-access suite passed all 10 checks. All 44 JavaScript suites passed. Browser acceptance complements these checks; it does not claim physical Android/iPhone installation or touch acceptance.

Automatic WhatsApp sync/sending still requires a connected eligible number and provider acceptance. Razorpay customer checkout, Google OAuth, real recovery-mail delivery and call/payment/shipping acceptance remain separate setup work. Manual WhatsApp handoff remains available meanwhile.
