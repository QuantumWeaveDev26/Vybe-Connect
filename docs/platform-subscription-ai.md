# Customer subscription and platform-funded AI

## 14 November update

Follow-up: authenticated AI state now exposes only safe current cooldown metadata, allowing Ask and agent screens to pause submission without exposing provider errors or credentials. A pause expires automatically; it does not change the subscription or reserve another request. Managed-customer errors direct users to their subscription or platform support, rather than requesting their own provider key. Billing-only and managed-AI access now share the same configured-plan/provider-identity checks, and an active subscription blocks another checkout on the server before any remote request.

Operators can run `python -B readiness.py` inside the existing runtime. It checks configuration only, prints no secrets, performs no network requests or data writes, and exits 2 because live-provider, mailbox, device and restore acceptance cannot be established by configuration. It neither activates services nor substitutes for Meta review or Razorpay merchant setup.

OpenAI 429 responses now distinguish provider quota/credit limits from rate limits when the provider supplies a code. A bounded per-key cooldown prevents repeated new submissions; existing responses can still be retrieved or cancelled. Known cooldowns are checked before reserving another included request. Explicit 401/403/404/429 rejections are recorded as failed rather than an uncertain submission. Network interruptions retain the unknown-outcome safeguards. Cooldowns are process-local and reset on restart; they are not a replacement for provider account limits.

Active subscriptions no longer offer another checkout, and authenticated, active or terminal subscriptions hide stale checkout URLs. Checkout remains unavailable without configured merchant credentials and verified provider plan IDs. This change does not create plans, authorize recurring payments, add API credits or establish live inference/payment acceptance.

The historical deployment notes below are dated evidence. Recheck runtime mode and provider readiness before enabling customer access.

When TW_PLATFORM_AI_MANAGED=true, new customer workspaces use the platform OpenAI key and gpt-6-luna. Customers cannot save/remove AI provider credentials or run platform provider diagnostics. They see subscription status, included requests and their WhatsApp connection. The operator retains service configuration screens; Services defaults to Subscription.

Verified Razorpay subscription state, current period end and a matching configured plan are required for customer AI. Core mutation access also requires an active subscription. Existing explicitly approved operator workspaces retain their current AI connection. Keys are never returned in public state. No customer token copying or fake subscription activation is used.

TW_PLATFORM_AI_DB defaults to TW_DATA_DIR/teamwave.db. Configure it explicitly for custom database paths. Missing storage, expired/cancelled subscriptions and unconfigured plans fail closed. The platform-wide TW_AI_ENABLED switch remains effective.

Each real AI model submission atomically reserves one request from that subscription billing cycle in SQLite. Unknown provider outcomes count and are never automatically resubmitted. Polling/cancellation do not consume another request. Plan ai_requests may be 1–1000; the safe default is 50. Suggested Starter/Growth/Scale allowances are 50/150/300 requests, not unlimited AI. Requests larger than 30,000 input bytes are rejected before reservation; Responses outputs remain bounded by the existing adapters. Direct embedding features remain unavailable for platform-funded customers until separately metered.

This is a per-cycle request allowance, not a rupee wallet or actual-cost ledger. The separate monetary AI allowances in the pricing proposal remain proposals. Invoice reconciliation, FX/tax treatment and cost-based top-ups are not implemented by this release.

Activate Razorpay by setting TW_BILLING_KEY_ID, TW_BILLING_KEY_SECRET, TW_BILLING_WEBHOOK_SECRET, TW_BILLING_ACCOUNT_ID, real TW_BILLING_PLANS, TW_BILLING_ENABLED and explicit live approval privately. Create real monthly INR plans at 49900, 99900 and 149900 minor units, with ai_requests 50, 150 and 300 respectively. Real plan prices are checked against Razorpay before checkout creation. No plan IDs or paid subscriptions were invented. Until merchant setup is complete, customers see a preparation message and cannot purchase or obtain paid CRM/AI access.

An active subscription does not bypass Meta approval, register a customer's number automatically or prove live messaging delivery. Customers still connect their own Meta business through the existing official onboarding flow.

## Customer-facing page cleanup

Templates now use concise approval guidance and show saved headers, body, footer and button labels in a larger message preview. This does not add media/carousel or OTP delivery support. Template rows adapt to narrow phones instead of hiding actions in a wide table. Inbox filters have comfortable targets and spacing. Workspace connections show VYBE AI as platform-provided; technical operator controls are folded. Customer billing excludes platform credential diagnostics entirely. Tablet section navigation no longer inherits full-height desktop sizing.

No new paid test prompt, Meta message, subscription authorization or transaction was submitted during this deployment. The earlier single synthetic OpenAI agent acceptance succeeded; it does not establish every live service or Meta onboarding flow.

## Deployment verification

Runtime source: f9e9041bebd4856b9a086612bcbac052145da08d. Hostinger VPS 1871828, project vybe-connect, deployment action 124026120 succeeded on 6 November 2026. App container healthy; source initializer exited 0. Live index and all 45 referenced JS/CSS assets matched the pinned commit byte for byte. Health/readiness returned 200, unauthenticated state 401, and private environment/source/database paths 404. Deployed Compose and environment exactly matched the intended candidate. Existing settings were preserved; platform AI managed mode, its authoritative database path and the already-authorized platform OpenAI key were added privately.

Validation: full Python discovery ran 680 tests with one skipped before final UI work; 28 focused platform-AI/business-service checks passed after the additional concurrency and plan-gate checks. All 29 JavaScript suites passed after the AI UI changes; all-route rendering passed after the final tablet CSS adjustment. These are local contract checks, not live payment or Meta acceptance.

Authenticated browser checks covered the four marked pages at a 390-pixel requested phone viewport, template rows at 320, connections at 768, and desktop inbox/templates/connections at 1531. Narrow rows and tablet navigation were visually checked after deployment. No page-wide horizontal overflow was observed on the four phone pages. No browser errors were captured in the final pass; temporary viewport overrides were restored. Physical-device acceptance and real customer checkout remain unverified. Local screenshots are in the current task workspace outputs/verification directory, outside the public application repository.
