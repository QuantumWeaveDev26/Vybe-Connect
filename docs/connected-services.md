# Connected services: deployment and acceptance

Implemented: Razorpay order payment links, provider reconciliation, cancellation, full refunds, signed and scoped webhooks; separate platform subscription account with real plan validation and cycle-end cancellation; Shiprocket India/INR booking, courier quotes, AWB, pickup, labels, tracking and cancellation reconciliation; isolated operator-provisioned client workspaces with hashed one-time owner invitations; inbound WhatsApp Calling signaling and browser audio; explicit read-only provider metadata checks.

## Configuration

Use `.env.production.example` as the variable-name reference. Keep secrets in the private Hostinger project environment, never Git or browser code. Replace WORKSPACE_ID with the actual uppercase workspace ID displayed in the workspace. Compose passes the private project `.env` into the app. Restart only the vybe-connect project after changing it.

Merchant payments use `TW_PAYMENTS_<WORKSPACE>_KEY_ID`, `KEY_SECRET`, `WEBHOOK_SECRET`, `ACCOUNT_ID`, `ENABLED` and `ALLOW_LIVE`. Platform subscriptions use the separate `TW_BILLING_` equivalents and `TW_BILLING_PLANS` JSON. Each plan must use a real Razorpay plan and the matching minor-unit amount, INR currency, monthly/yearly interval and cycle count. Test keys are supported; live keys additionally require ALLOW_LIVE. Keep both activation flags false until an approved acceptance test.

Razorpay webhooks: `https://YOUR_HOST/razorpay-webhook/payments/WORKSPACE_ID` and `/razorpay-webhook/billing/WORKSPACE_ID`. Configure each account's matching secret and ACCOUNT_ID. Only raw-body HMAC-valid, correctly scoped provider resources update state. Redirects do not prove payment. Unknown or interrupted outcomes require reconciliation, never blind retry. Definitively failed operations can be explicitly released for a corrected request, preserving audit history.

Shiprocket uses `TW_SHIPPING_<WORKSPACE>_TOKEN`, `PICKUP_LOCATION`, `PICKUP_POSTCODE`, `ENABLED`. Use an existing pickup location. Address/package details are requested at booking; prepaid booking requires a verified paid order, otherwise choose COD. Courier quotes expire. Pickup and booking can incur charges. No automatic retry or automatic local fulfillment. Order cancellation cannot restore stock while payment or shipment obligations remain unresolved.

Onboarding uses `TW_PLATFORM_OWNER_EMAIL` matching the authenticated operator. It provisions a client workspace and one-time invitation; share that link privately yourself. It does not send an email or complete Meta Embedded Signup. `TW_BILLING_ENFORCE` remains false until subscription acceptance succeeds.

Inbound calling uses existing workspace Meta credentials, signed Meta calls events and `TW_CALLING_<WORKSPACE>_ENABLED`. Optional `TURN_URLS` and `TURN_SECRET` generate short-lived coturn REST credentials. Require HTTPS, an eligible Meta number, permission to use the microphone and real two-device audio testing. Outbound permission requests/dialing, recording and transfers are not implemented.

Provider metadata checks require `TW_PROVIDER_READS=true`. OpenAI checks retrieve model metadata without inference. Checks expire after 24 hours and when credential fingerprints change. A successful metadata check is not payment, shipment, messaging, AI-answer or audio acceptance.

## Acceptance still required

Before production service: owner account setup and MFA; real approved test-key payment/subscription and signed webhook lifecycle; shipping account confirmation and approved booking/cancellation; Meta number eligibility and signed incoming call plus two-device audio; AI response testing; backup restore and operational monitoring. No chargeable provider actions were run during implementation. Exact WATI visual/functional parity is not established by these integrations. Keep public review read-only; it contains sample data and cannot submit provider actions.

The opening screen adapts the supplied video's dotted animated mark using VYBE branding, reduced-motion support, first-render dismissal and an eight-second fallback. It is not a placeholder destination or a provider progress indicator.
