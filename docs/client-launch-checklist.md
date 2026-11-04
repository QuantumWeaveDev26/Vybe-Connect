# Client launch verification

## Current decision: not cleared for client production use

The application can be deployed and inspected, but server health is not business-service readiness. The live bootstrap on November 4 reported no initialized real owner account. The public root is an isolated, explicitly read-only sample store. Preview records do not become client data. Create the real owner at /owner using the existing private setup token, then configure real workspace-scoped providers using ENVIRONMENT_SETUP.md.

## Verified in this release

- 517 Python regression tests passed in 256.999 seconds, including new authenticated profile HTTP tests, CSRF/session rejection, immutable email/role fields, durable profile names and unchanged login/membership access.
- JavaScript renderer, navigation, privacy, template selection, avatar input safety and cleanup checks passed.
- In an isolated real signed-in browser workspace: display-name edit saved and reopened; Refresh confirmed current state; AI panel opened and disabled sending without configuration; manual agent creation saved exactly one permitted action and reopened the exact checkbox selection.
- Permission checkboxes measured 18 by 18 pixels with aligned labels. At 375px content width profile and Refresh remained reachable and no document-level horizontal overflow occurred. No browser console errors appeared.
- World map geometry now centers at half the viewport height. Green visual theme is retained. Card/rail hover depth applies on precise pointers, with reduced-motion alternatives. Browser pointer interaction confirmed a real card transform of translateY(-4px) and the expected shadow. No fabricated AI replies or provider outcomes were introduced.

## Mandatory before inviting paying clients

1. Create/sign in to the real owner account. Verify the actual workspace ID; do not configure the preview ID or WATI account ID. Test an owner and an invited agent in separate sessions, least-privilege access, password recovery and MFA.
2. Configure Meta developer app, eligible WABA/phone, scoped token, app secret, verification token and Graph version. Verify signed inbound and delivery/read webhooks. Approve a controlled outbound/template test and confirm real receipt; check service-window/consent gates.
3. Configure OpenAI and approved model. Approve limited inference, validate grounded answers, citations and human handoff. Check agent scheduling and action-review behavior against real workspace facts before allowing customer auto-replies.
4. Validate Razorpay test-key links, captured payment/refund and subscription lifecycles with signed events. Keep platform billing separate from merchant payments. Do not enforce subscriptions until acceptance.
5. Approve a Shiprocket shipment, label/pickup/tracking/cancellation test with a real account. Review charge and uncertain-outcome recovery behavior.
6. Validate an eligible Meta inbound call over HTTPS with two real devices, microphone access and TURN connectivity. Outbound calls, recording and transfers remain unfinished.
7. Run a production backup/restore drill and configure monitoring, support ownership, retention and incident procedures. Perform actual-device accessibility and browser checks for client deployments.

## Remaining product gaps

Full WATI feature parity remains incomplete. Self-service Meta onboarding, outbound calling/transfer/recording and additional WATI channels/tool coverage are not completed by entering API keys. Provider acceptance was not performed in this release. No paid API inference, WhatsApp message, charge, refund, shipment or call was initiated.

The existing public preview stays isolated and read-only to support review without bypassing owner authentication. Fake customer records and fake provider responses must never be added to real workspaces. When ready, TW_PUBLIC_REVIEW=false removes public sample access.
