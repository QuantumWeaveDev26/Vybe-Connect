# AI activation and calling release — 2026-11-04

## Live AI
The owner approved enabling OpenAI for real user/customer usage only, while forbidding paid testing. TW_AI_ENABLED=true and TW_AI_EAA91C5FE6F20007_ALLOW_PAID=true are now live. Existing Daily Digest is on demand; its Run now button is enabled. No prompt was submitted and no credits were used for testing. Automatic customer replies remain disabled. Real usage can incur OpenAI charges.

## Calling implementation
- Existing inbound signed offers, single-teammate claims, browser answers, decline and hang-up retained.
- Added provider call-permission checks, explicit permission requests within the 24-hour window, and outbound browser dialing.
- Separate disabled-by-default OUTBOUND_ENABLED gate. Each dial rechecks provider permission and rejects expired temporary grants.
- Durable request IDs prevent duplicate connects. Uncertain POST outcomes do not automatically retry. Late signed answers reconcile uncertain attempts; terminal events take precedence.
- SDP answers are private to the initiating teammate, excluded from shared state. Local microphone, peer and polling resources are cleaned up.
- Call and permission-request history use actual persisted operations. No fabricated calls or sample records.

## Validation
12 outbound backend regression tests, 18 existing business-service tests and 28 HTTP tests passed. All 15 JavaScript files passed, including the mocked WebRTC offer/answer workflow and cleanup. No live audio/call test or permission message was sent. Previous 541-test full run belongs to the preceding release, not this new calling patch.

Source review found a late-answer reconciliation race; fixed with a dedicated test. API research used PyWa's primary implementation at https://github.com/david-lev/pywa/blob/master/pywa/api.py (call_permissions and calls/connect). Meta calling documentation links were throttled during this review; live eligibility and provider contract acceptance remain unverified.

## Activation still required for calling
Calling is not enabled in production. Configure an eligible Meta number and webhook subscription first; correct the failed Meta metadata check. Set TW_CALLING_EAA91C5FE6F20007_ENABLED and, separately, TW_CALLING_EAA91C5FE6F20007_OUTBOUND_ENABLED only after provider authorization. Configure TURN_URLS and TURN_SECRET for reliable WebRTC connectivity. Permission-request messages also require the Meta LIVE gate and an open service window. No calling gate or messaging gate was enabled by this release.

Recording and transfer, complete self-service client Meta onboarding, payment/shipping/billing credentials and live acceptance remain outstanding. This release is not full WATI parity or all-service production clearance.
