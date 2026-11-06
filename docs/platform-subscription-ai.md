# Customer subscription and platform-funded AI

When TW_PLATFORM_AI_MANAGED=true, new customer workspaces use the platform OpenAI key and gpt-6-luna. Customers cannot save/remove AI provider credentials or run platform provider diagnostics. They see subscription status, included requests and their WhatsApp connection. The operator retains service configuration screens; Services defaults to Subscription.

Verified Razorpay subscription state, current period end and a matching configured plan are required for customer AI. Core mutation access also requires an active subscription. Existing explicitly approved operator workspaces retain their current AI connection. Keys are never returned in public state. No customer token copying or fake subscription activation is used.

TW_PLATFORM_AI_DB defaults to TW_DATA_DIR/teamwave.db. Configure it explicitly for custom database paths. Missing storage, expired/cancelled subscriptions and unconfigured plans fail closed. The platform-wide TW_AI_ENABLED switch remains effective.

Each real AI model submission atomically reserves one request from that subscription billing cycle in SQLite. Unknown provider outcomes count and are never automatically resubmitted. Polling/cancellation do not consume another request. Plan ai_requests may be 1–1000; the safe default is 50. Suggested Starter/Growth/Scale allowances are 50/150/300 requests, not unlimited AI. Requests larger than 30,000 input bytes are rejected before reservation; Responses outputs remain bounded by the existing adapters. Direct embedding features remain unavailable for platform-funded customers until separately metered.

This is a per-cycle request allowance, not a rupee wallet or actual-cost ledger. The separate monetary AI allowances in the pricing proposal remain proposals. Invoice reconciliation, FX/tax treatment and cost-based top-ups are not implemented by this release.

Activate Razorpay by setting TW_BILLING_KEY_ID, TW_BILLING_KEY_SECRET, TW_BILLING_WEBHOOK_SECRET, TW_BILLING_ACCOUNT_ID, real TW_BILLING_PLANS, TW_BILLING_ENABLED and explicit live approval privately. Create real monthly INR plans at 49900, 99900 and 149900 minor units, with ai_requests 50, 150 and 300 respectively. Real plan prices are checked against Razorpay before checkout creation. No plan IDs or paid subscriptions were invented. Until merchant setup is complete, customers see a preparation message and cannot purchase or obtain paid CRM/AI access.

An active subscription does not bypass Meta approval, register a customer's number automatically or prove live messaging delivery. Customers still connect their own Meta business through the existing official onboarding flow.
