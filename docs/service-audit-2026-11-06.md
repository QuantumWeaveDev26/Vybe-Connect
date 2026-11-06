# VYBE Connect service audit — 6 November 2026

## Scope and limits

No paid AI inference, Meta messages/calls, payment/refund/subscription creation, shipment booking, live SMTP delivery or production sample records were used. Provider contracts were verified with isolated test doubles. Automated/local behavior, deployed assets, browser rendering and live-provider acceptance are separate claims.

## Issues found and repaired

- Meta form status sync could interrupt an active operation. Active requests now retain their operation marker until completion or a bounded stale/uncertain reconciliation point.
- A fresh nonce could retry an unknown form send. The same form/customer is now held while a prior send remains submitting/unknown, including after publication-status sync. A verified correlated customer submission can establish completion.
- A fast form submission could arrive before a late provider result. Completion is now preserved across later failures, acceptance results and delivery receipts. Form-send history is visible without exposing correlation tokens.
- Uncertain remote form creation had no customer reconciliation path. Administrators can link an existing unpublished draft only after Meta confirms its name and connected WABA. The definition must be uploaded again before publication. Wrong-account/name/published drafts are rejected.
- Invalid provider response shapes now become sanitized uncertain results, not false success or an unhandled response exception.
- Recipe contact creation and Support tools Resolve actions now invoke the existing contact-created/conversation-resolved rule events once within the same transaction.
- One-time dialog secrets are also scrubbed on programmatic close, and late modal errors are displayed safely after a dialog/account change.

## Acceptance evidence

Initial full discovery: 649 tests, 648 passed and one POSIX-only permission check skipped on Windows. All 27 JavaScript suites pass. New regression tests reproduced the form-sync and duplicate-send failures before repair, then passed. Final affected server/HTTP/provider contract run: all 110 tests passed in 69.470 seconds, including Store, HTTP, growth, rule events, Meta contracts and rich delivery.

REA isolated browser: all 26 authenticated page routes completed navigation at 320 x 740 with no page errors. At 390 x 844, real browser actions persisted macro reply drafts/private notes/tags, snooze, branch assignment, a published help article, a paused webhook recipe and a secret rotation. HTTP readback confirmed these records and the publicly readable article. Unconfigured Meta creation correctly reported Connect WhatsApp first without making a provider request. An initial browser automation step used a selector matching both close buttons; that harness selector was corrected and the remaining path completed. All fixtures were in a temporary database; none were deployed.

## Still not established by this audit

Real Meta onboarding/approval and Flow create/upload/publish/send acceptance; paid AI inference and agent outcomes; live calling/audio; payment/shipping/subscription acceptance; recovery email arrival; native Google/Zoho/WooCommerce connections; branch visibility restrictions; physical-device behavior and complete WATI parity. Existing test doubles do not prove these integrations work with real accounts. No readiness percentage or full production-service clearance is claimed.
