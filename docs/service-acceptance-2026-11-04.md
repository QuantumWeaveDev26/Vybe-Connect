# Service acceptance audit — 2026-11-04

This is a verification record, not production clearance.

## Changes
- Meta metadata checks require phone access, membership in the configured WABA and template access. Requests include app-secret proof. Old check fingerprints expire after the checker change.
- Readable 13–14px supporting text and controls in core workspace and agent screens.
- Once-only scroll entry and subtle hover feedback; content stays visible without JavaScript. Reduced-motion preference disables animations.
- Clear HTTP error messages during restarts instead of raw JSON parsing errors; no automatic mutation retries.
- Commerce policy is an optional disclosure rather than repeated full-page copy.

## Current blockers from private configuration
- OpenAI key exists; inference and paid-call approval are disabled. User explicitly requires zero spend/credits. No live inference test is authorized.
- Razorpay order payment and billing credentials, verified plans, and Shiprocket connection settings are missing. No payment, shipment, pickup, refund or subscription was created.
- Meta sending remains off. No outbound WhatsApp message or calling action was performed.
- Recovery mail remains disabled pending SMTP acceptance.
- External-agent directory has no configured agents. No fake integration has been added.
- Public preview and message simulation remain disabled. Customer data is not populated with demos.

## Environment fields required for the missing services
Keep secrets in the private Hostinger project environment, not this file or GitHub.

Order payments: TW_PAYMENTS_EAA91C5FE6F20007_KEY_ID, KEY_SECRET, WEBHOOK_SECRET, ACCOUNT_ID using the same prefix for each key.
Shipping: TW_SHIPPING_EAA91C5FE6F20007_TOKEN, PICKUP_LOCATION, PICKUP_POSTCODE using the same prefix.
Platform billing: TW_BILLING_KEY_ID, TW_BILLING_KEY_SECRET, TW_BILLING_WEBHOOK_SECRET, TW_BILLING_ACCOUNT_ID and TW_BILLING_PLANS with actual provider plan IDs.
Activation flags remain false until the specific service acceptance and spending authorization are complete.

## Remaining implementation limits
Outbound WhatsApp calling, transfer/recording and self-service Meta Embedded Signup remain incomplete. Full WATI parity is not established by passing contract tests.

## Verification and changes
- Initial broad run: 539 of 540 tests passed. The missing interaction-asset route failed as expected in the server process that started before its fix.
- After the fix: all 28 HTTP tests, all 11 deployment tests and all 4 Meta-readiness regression tests passed. A fresh complete suite is running.
- All 14 JavaScript test files passed, including all 21 rendered routes, agent presets, API errors, entry-animation behavior and reduced motion.
- Source review found the missing interaction-script route; fixed and covered by an entrypoint-asset serving test.
- Removed duplicate contextual tab navigation, corrected production simulation instructions, and shortened connection setup copy. Scoped OpenAI environment name now matches the actual workspace key.
- No production records deleted or seeded, and no provider calls that consume credits were made.
