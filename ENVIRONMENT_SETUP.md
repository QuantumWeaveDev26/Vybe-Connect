# VYBE Connect: environment setup

Use the private **Hostinger VPS > Docker > vybe-connect > Environment** for values. Never commit the real environment or paste tokens in chat. Preserve the current TW_SETUP_TOKEN and production data volume. Redeploy only vybe-connect after changing variables.

## First: real owner workspace

The root site is an explicitly read-only preview. Go to `/owner`, create/sign in to your owner account using the existing private setup token, then open Settings. Copy the variable prefix shown there. Replace WORKSPACE_ID below with your real VYBE workspace ID in uppercase. **Do not use WATI's 10248278 or the public preview workspace ID.** Keys do not create an owner account or migrate WATI data. When TW_PLATFORM_OWNER_EMAIL is configured before setup, the initial account email must match it; the private setup token remains required.

## Minimum: WhatsApp and OpenAI

```dotenv
TW_PUBLIC_ORIGIN=https://vybe.srv1871828.hstgr.cloud
TW_PLATFORM_OWNER_EMAIL=YOUR_OWNER_ACCOUNT_EMAIL
# Keep the existing random TW_SETUP_TOKEN; do not replace it with an example.

TW_META_WORKSPACE_ID_TOKEN=YOUR_META_SYSTEM_USER_ACCESS_TOKEN
TW_META_WORKSPACE_ID_PHONE_ID=YOUR_PHONE_NUMBER_ID
TW_META_WORKSPACE_ID_WABA_ID=YOUR_WHATSAPP_BUSINESS_ACCOUNT_ID
TW_META_WORKSPACE_ID_APP_SECRET=YOUR_META_APP_SECRET
TW_META_WORKSPACE_ID_VERIFY_TOKEN=YOUR_OWN_RANDOM_WEBHOOK_VERIFY_STRING
TW_META_WORKSPACE_ID_VERSION=YOUR_APP_SUPPORTED_GRAPH_VERSION
TW_META_WORKSPACE_ID_LIVE=false
TW_META_WORKSPACE_ID_FLOW_SEND=false

TW_AI_PROVIDER=openai
TW_AI_MODEL=gpt-6-luna
TW_OPENAI_API_KEY=YOUR_OPENAI_API_KEY
TW_AI_ENABLED=false
TW_AI_WORKSPACE_ID_ALLOW_PAID=false
TW_AI_WORKSPACE_ID_AUTO_REPLY=false
# Optional tenant-specific key, overriding the shared key:
TW_AI_WORKSPACE_ID_OPENAI_API_KEY=
TW_PROVIDER_READS=false
```

Use a model available to your OpenAI project. The current model catalog lists GPT-6 Luna: https://developers.openai.com/api/docs/models/all . A model metadata check is not a paid AI-response acceptance test.

Meta callback: `https://vybe.srv1871828.hstgr.cloud/webhook/YOUR_WORKSPACE_ID` (path uses the actual ID as shown in Settings, not its uppercase variable form). Subscribe the app to the correct WABA and signed message events. Calling also needs an eligible number and signed calls events. Business verification and WATI's connection do not supply these credentials automatically.

After your approved live test, manual messaging/campaigns require LIVE=true. Automated workflow delivery additionally requires FLOW_SEND=true. AI generation requires both TW_AI_ENABLED=true and the workspace ALLOW_PAID=true. Customer auto-replies additionally require AUTO_REPLY=true, enabled assistant configuration, approved knowledge, live reply mode, Meta sending and the applicable service window. Setting these flags can incur provider costs; none were enabled during this release.

## Optional: order payments

```dotenv
TW_PAYMENTS_WORKSPACE_ID_KEY_ID=YOUR_RAZORPAY_KEY_ID
TW_PAYMENTS_WORKSPACE_ID_KEY_SECRET=YOUR_RAZORPAY_KEY_SECRET
TW_PAYMENTS_WORKSPACE_ID_WEBHOOK_SECRET=YOUR_PAYMENT_WEBHOOK_SECRET
TW_PAYMENTS_WORKSPACE_ID_ACCOUNT_ID=YOUR_RAZORPAY_ACCOUNT_ID
TW_PAYMENTS_WORKSPACE_ID_ENABLED=false
TW_PAYMENTS_WORKSPACE_ID_ALLOW_LIVE=false
```

Webhook: `/razorpay-webhook/payments/YOUR_WORKSPACE_ID`. Razorpay test keys first. ENABLED=true permits the connector; live keys also need ALLOW_LIVE=true. Payment completion comes from signed provider evidence, not a checkout redirect.

## Optional: platform subscriptions

Use separate platform billing credentials, not a client's merchant payment credentials:

```dotenv
TW_BILLING_KEY_ID=YOUR_PLATFORM_RAZORPAY_KEY_ID
TW_BILLING_KEY_SECRET=YOUR_PLATFORM_RAZORPAY_KEY_SECRET
TW_BILLING_WEBHOOK_SECRET=YOUR_BILLING_WEBHOOK_SECRET
TW_BILLING_ACCOUNT_ID=YOUR_PLATFORM_RAZORPAY_ACCOUNT_ID
TW_BILLING_ENABLED=false
TW_BILLING_ALLOW_LIVE=false
TW_BILLING_ENFORCE=false
TW_BILLING_PLANS={}
```

Map real Razorpay plans in TW_BILLING_PLANS; see docs/connected-services.md for the exact JSON schema. Configure the billing webhook at `/razorpay-webhook/billing/YOUR_WORKSPACE_ID`. Keep enforcement off until subscription acceptance succeeds. The platform owner can provision isolated client workspaces and one-time invitations. Self-service Meta Embedded Signup remains unfinished.

## Optional: Shiprocket shipping

```dotenv
TW_SHIPPING_WORKSPACE_ID_TOKEN=YOUR_SHIPROCKET_API_TOKEN
TW_SHIPPING_WORKSPACE_ID_PICKUP_LOCATION=YOUR_EXISTING_PICKUP_LOCATION_NAME
TW_SHIPPING_WORKSPACE_ID_PICKUP_POSTCODE=YOUR_SIX_DIGIT_PICKUP_POSTCODE
TW_SHIPPING_WORKSPACE_ID_ENABLED=false
```

The implemented booking workflow uses India/INR. ENABLED=true permits requests which can incur charges. Supply a real address and package details at booking; verify paid status for prepaid orders. Confirm account permissions and an approved shipment/cancellation before client use.

## Optional: inbound WhatsApp calls

```dotenv
TW_CALLING_WORKSPACE_ID_ENABLED=false
TW_CALLING_WORKSPACE_ID_TURN_URLS=turn:YOUR_RELAY_HOST:3478
TW_CALLING_WORKSPACE_ID_TURN_SECRET=YOUR_COTURN_REST_SHARED_SECRET
```

Requires the Meta configuration above, eligible number, HTTPS, microphone permission and real two-device audio verification. TURN credentials are short-lived and derived server-side. Outbound calling, recording and transfer workflows remain unfinished.

## Other optional connectors

The complete `.env.production.example` includes SMTP password recovery, Shopify, external agent webhooks and website knowledge origin allowlists. Connection setup in each workspace shows the exact scoped names. Enable recovery only after SMTP acceptance. External agents use the application's documented signed contract, not WATI's private backend.

Set TW_PUBLIC_REVIEW=false only when you are ready to stop public preview. Preserve TW_SANDBOX=false in production. Keep TW_BILLING_ENFORCE=false until billing is accepted. Environment variables do not complete missing functionality, provider approvals or live acceptance; they configure the implemented adapters.
# Public business registration

After initial owner setup, set `TW_PUBLIC_SIGNUP=true` to allow customers to create their own isolated business accounts at `/#signup`. It defaults to false. This does not expose the owner setup token or join new users to the operator's workspace. Initial owner creation remains protected separately.

Sign-in and signup offer Keep me signed in for 30 days. Sessions use secure server-backed cookies; passwords are not stored in browser storage. Logout and password/security changes revoke sessions. Public signup does not verify ownership of the email address or activate provider integrations automatically.
