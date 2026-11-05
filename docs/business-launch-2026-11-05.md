# Business launch checkpoint — 2026-11-05

## Product goal
VYBE Connect is an independently operated business-messaging platform intended to replace the WATI subscription for the workflows a customer needs. Hosting, Meta usage and approved AI usage remain direct operating expenses; no pricing savings or completed live delivery is claimed without evidence.

## Core messaging launch
The application implements shared inbox, contacts/tags/fields, templates, broadcasts, automation, teams, knowledge-backed AI, agent findings and tenant isolation. OpenAI remains enabled for real usage only. No inference, call or billable transaction was executed for testing.

The current concrete blocker is Meta account access: the live metadata check returned HTTP 401 and Meta code 190, rejecting the stored access token. The new diagnostics distinguish phone access, WABA access, mismatched pairing and template permissions. Only numeric error codes are retained; provider response messages and tokens are not exposed.

A valid replacement token must reach the private running configuration, then the account/phone pairing and template access must pass. Webhook receipt and real messaging acceptance remain distinct from metadata checks. The assistant cannot mark those complete without observing them.

## Optional service lines
Commerce, Razorpay subscriptions and Shiprocket are separate integrations, not dependencies of the basic shared inbox. They remain unconfigured and must not be sold as active integrations. Calling code supports inbound/outbound signaling and browser audio, but remains disabled pending Meta eligibility, TURN and live acceptance. Recording/transfer and complete Embedded Signup remain unfinished.

## This release
Application commit 07fbac5a7836d94f5a37b016c2979a06c104d0c7, successful Hostinger action 123770563. Diagnostics and theme assets match source; healthz and readyz return 200. Approved AI and private environment values preserved.

39 targeted Python tests passed: seven Meta readiness, two transport diagnostics, eighteen business services and twelve outbound calling tests. All fifteen JavaScript checks passed. Code review found no actionable diagnostics issues. These are local/mocked test results rather than live transaction acceptance.

## Credential handoff
After the owner replied Saved, Hostinger still contained the same token override and environment; the existing private token file had not changed since 2026-11-04. The replacement location was requested without asking for a token in chat. Keep tokens out of GitHub and browser-visible application fields.

## Meta token replacement verified — 2026-11-05
The owner saved a changed token in the existing private token file. It was loaded without displaying it and deployed in the private Compose override by successful Hostinger action 123772321. The rest of the environment was unchanged; application source stayed pinned to 07fbac5a7836d94f5a37b016c2979a06c104d0c7.

Live Meta metadata verification now PASSED: phone access, configured phone membership in its WABA and template access. The authenticated Services screen displays Metadata verified. This supersedes the earlier rejected-token blocker. No WhatsApp message, AI inference, permission request or call was executed for testing. Healthz and readyz return200; unauthenticated api/state401 and .env404.

Live sending activation was requested separately for real usage because actual messages may incur provider charges. At this checkpoint the sending flag is unchanged and remains off. Calling, payment/shipping credentials and live delivery/audio acceptance remain separate work.
