# Client launch verification

## Current decision: not cleared for client production use

The real owner account has been created and the public sample workspace is disabled. Current live bootstrap reports initialized=true and review_available=false. Owner creation and preview removal are completed gates; do not ask the user to repeat them. Provider credentials, live acceptance and the product gaps below still prevent client-production clearance. Use ENVIRONMENT_SETUP.md for real workspace configuration.

## Verified in this release

- Latest full regression: 518 Python tests passed in 267.512 seconds, including production owner-email binding, authenticated profile HTTP tests, CSRF/session rejection, immutable email/role fields, durable profile names and unchanged login/membership access.
- JavaScript renderer, navigation, privacy, template selection, avatar input safety and cleanup checks passed.
- In an isolated real signed-in browser workspace: display-name edit saved and reopened; Refresh confirmed current state; AI panel opened and disabled sending without configuration; manual agent creation saved exactly one permitted action and reopened the exact checkbox selection.
- Permission checkboxes measured 18 by 18 pixels with aligned labels. At 375px content width profile and Refresh remained reachable and no document-level horizontal overflow occurred. No browser console errors appeared.
- World map geometry now centers at half the viewport height. Green visual theme is retained. Card/rail hover depth applies on precise pointers, with reduced-motion alternatives. Browser pointer interaction confirmed a real card transform of translateY(-4px) and the expected shadow. No fabricated AI replies or provider outcomes were introduced.

## Mandatory before inviting paying clients

1. Owner signup is complete. Verify the invited-agent lifecycle in separate sessions, least-privilege access, password recovery and MFA. Use the real VYBE workspace ID, not the old preview ID or WATI account ID.
2. Configure Meta developer app, eligible WABA/phone, scoped token, app secret, verification token and Graph version. Verify signed inbound and delivery/read webhooks. Approve a controlled outbound/template test and confirm real receipt; check service-window/consent gates.
3. Configure OpenAI and approved model. Approve limited inference, validate grounded answers, citations and human handoff. Check agent scheduling and action-review behavior against real workspace facts before allowing customer auto-replies.
4. Validate Razorpay test-key links, captured payment/refund and subscription lifecycles with signed events. Keep platform billing separate from merchant payments. Do not enforce subscriptions until acceptance.
5. Approve a Shiprocket shipment, label/pickup/tracking/cancellation test with a real account. Review charge and uncertain-outcome recovery behavior.
6. Validate an eligible Meta inbound call over HTTPS with two real devices, microphone access and TURN connectivity. Outbound calls, recording and transfers remain unfinished.
7. Run a production backup/restore drill and configure monitoring, support ownership, retention and incident procedures. Perform actual-device accessibility and browser checks for client deployments.

## Remaining product gaps

Full WATI feature parity remains incomplete. Self-service Meta onboarding, outbound calling/transfer/recording and additional WATI channels/tool coverage are not completed by entering API keys. Provider acceptance was not performed in this release. No paid API inference, WhatsApp message, charge, refund, shipment or call was initiated.

TW_PUBLIC_REVIEW=false is already configured in production. The optional sample implementation remains available for isolated local review only. Fake customer records and fake provider responses must never be added to real workspaces.

## Historical deployment verification

Application d75f127152f55f958f5b41f930bf5c2468d47280 deployed by Hostinger action 123604854. Source initializer exited 0 and app became healthy. HTTPS healthz/readyz returned 200; all 34 frontend/data assets matched source. Unauthenticated profile POST returned 401. Live browser verified Refresh confirmation, correctly read-only preview profile and five aligned 18x18 permission checkboxes, without console errors. The authenticated profile update and agent-permission persistence tests ran against an isolated QA store, not customer production data.

## Current owner transition

Owner-binding application 5a48994ab74059fec2723203cd4f584e0a60e9ea is pinned in deploy/hostinger_source_init.py. After deployment, the user created the real owner account privately and accessed its Settings screen. Meta/OpenAI configuration names were prepared in the private environment, but their credential values remain empty and live/paid gates remain off. Meta developer setup is the next user-assisted step.
