# Real service connections

The implementation connects to real APIs when configured. It has not been verified against your Meta account because your developer/API setup does not exist yet. The AI runtime is also not installed/running at the checked local endpoint.

## Meta WhatsApp Cloud API

1. Sign into Meta for Developers using your own business account and create/configure an app for WhatsApp Business messaging. Follow Meta's current dashboard instructions; handle account agreements and verification yourself.
2. Identify the developer app, WhatsApp Business Account ID (WABA), phone number ID and supported Graph API version. Obtain the app secret, webhook verify token and an access token with appropriate WhatsApp permissions. Do not paste these into chat or client-side code.
3. Open TeamWave, create your business owner account, then open Settings → WhatsApp Cloud API. It displays the exact environment variable prefix for that business workspace.
4. Copy `.env.example` to `.env` beside `server.py`; replace `WORKSPACE_ID` with the displayed uppercase workspace ID. Enter credentials locally, then restart the server.
5. Use **Sync from Meta** in Template Messages. Local drafts are not provider approvals. **Submit to Meta** creates a real provider review request for a new text template; approval status comes from a subsequent provider sync. Current sync retrieves up to 100 templates and reports whether more remain.
6. Live campaigns require a synced APPROVED template and `LIVE=true` for that workspace. Launching queues actual messages for opted-in recipients. The local background worker submits one claimed job at a time. Scheduled campaigns use ISO timestamps with timezone offsets. Queue state survives restart; uncertain or interrupted jobs are not automatically repeated.
7. Manual free-form replies require a real inbound webhook within the 24-hour customer service window. Sandbox messages do not open this window.

Meta webhooks require a publicly accessible HTTPS callback. This development server is intentionally loopback-only and rejects arbitrary Host headers. A production HTTPS service, supported proxy configuration and deployment/security work are required before Meta can deliver webhooks directly to it. Do not expose the development server by opening a public port.

The callback path is `/webhook/<workspace-id>`. Verification uses the workspace's configured verify token. POST events require HMAC-SHA256 using that app secret and a matching configured phone number ID. Delivered/read states come from received provider events, not from local inference.

Your existing phone number is currently connected through WATI. Do not disconnect or migrate it during initial development. Plan the number connection or migration separately so your existing customer service is not interrupted.

Official reference: [Meta's WhatsApp API workspace](https://www.postman.com/meta/whatsapp-business-platform/documentation/wl), [messages endpoint](https://www.postman.com/meta/whatsapp-business-platform/folder/o48mro7/messages), [template endpoint](https://www.postman.com/meta/whatsapp-business-platform/folder/huymv7d/templates).

## AI assistant panel

The **TeamWave AI** button opens a WATI-inspired Ask/Agents panel. It stores private per-user chat history, uses the selected workspace's real counts and template/campaign records, and supports saved agent instructions. The model has no direct write tools and cannot launch campaigns or send messages. On-demand analyses can propose bounded local actions as pending findings. An administrator must review and apply each proposal. See docs/adopted-features.md for the supported action list, stale-data checks and limits.

The app supports **OpenAI** and **local Ollama**. Set `TW_AI_PROVIDER` and `TW_AI_MODEL` in `.env`. For OpenAI, store `TW_OPENAI_API_KEY` locally, or use `TW_AI_<UPPERCASE_WORKSPACE_ID>_OPENAI_API_KEY` for a business-specific key. The recommended starting model is `gpt-6-luna`; choosing another model is an explicit server configuration change, with no automatic escalation.

OpenAI remains disabled until both `TW_AI_ENABLED=true` and `TW_AI_<UPPERCASE_WORKSPACE_ID>_ALLOW_PAID=true` are explicitly set. The supplied local `.env` template leaves calls disabled. Restart the server after changes. Settings shows each workspace's exact prefix without exposing keys. Do not put keys in chat or browser fields. Creating a workspace owner login is required before a workspace-specific Meta or AI connection can be configured.

For Ollama set `TW_AI_PROVIDER=ollama`, the exact installed model name, `TW_AI_ENABLED=true`, and optionally `TW_AI_URL` (default loopback port 11434). The app does not install the runtime or download models. An unavailable provider produces an explicit error, never a simulated answer.

The agent worker runs while the server is running. Schedules are opt-in per agent and can use paid API calls when that business's gate is enabled. Archive stops publication by existing runs; pause stops future scheduling. Missed intervals are skipped. See [background AI release](docs/background-ai-release.md) for scope and verification boundaries.

Official references: [OpenAI Responses](https://developers.openai.com/api/docs/guides/text), [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Ollama chat API](https://docs.ollama.com/api/chat).

## Serving other businesses

Workspaces, memberships, two roles, scoped records, per-workspace Meta environment names and a persistent queue are implemented. This is still a development application. Public onboarding, Meta business/client authorization, encrypted secret management, TLS, production authentication/recovery, rate limits, backups, monitoring, durable deployment and security review remain required before offering a hosted service to customers.

## Attachment and Shopify increment

Outbound attachments use the existing tenant Meta settings and LIVE gate. Uploading a selected file contacts Meta even before sending, then retains a private copy under the database directory. See [media scope](docs/media-adapter.md). Shopify uses separate TW_SHOPIFY_<UPPERCASE_WORKSPACE_ID>_SHOP, TOKEN, API_VERSION and WEBHOOK_SECRET variables; see [connector scope](docs/shopify-connector.md). Read-only sync is initiated explicitly in Commerce & Integrations. All provider verification is still pending.

## External agents and developer webhooks

Create a connection in Custom AI Agents and use Connection setup for the exact server variables. Dispatch remains disabled until its workspace gate, public HTTPS origin allowlist and signing secret are configured. Signed callbacks create unsent reply drafts only. API keys and live verification are deferred at the user's request. See [the event and callback contract](docs/external-agents.md).

## Optional live chatbot delivery

Chatbots default to unsent drafts. Preparing a live flow does not authorize server sending. After an approved live test is scheduled, live chatbot text also requires `TW_META_WORKSPACE_ID_FLOW_SEND=true`, complete/live Meta settings, a current admin owner and a real customer service window. Keep this flag false while developing. Source config examples contain no secrets. See docs/live-chatbot-delivery.md for checkpoint, cancellation and unknown-result behavior.
