# Optional AI gateway connection

This is original VYBE code, not copied New API, Routerly or Evolution source. No additional gateway implementation license is introduced into VYBE by this adapter. Running a third-party gateway still requires complying with that service's own license; this adapter does not remove those obligations.

## Delivered behavior

* Platform-controlled HTTPS gateway catalog with approved model IDs. Customers cannot supply arbitrary destination URLs.
* Workspace-scoped keys use the existing encrypted AI credential store. Switching providers requires a new key; active requests block key/provider removal so in-flight handling retains its credentials.
* Queued AI Ask, agent creation, scheduled findings and grounded customer assistants can use a Responses-compatible gateway. Strict structured-output contracts and existing human approval / live-send controls remain in place.
* Blocking Responses requests are used because a compatible API does not prove background polling or remote cancellation support. Stop can discard a result locally; it does not guarantee that the upstream model stopped generating or billing.
* Each submitted gateway request reserves one unit from a workspace daily request cap, atomically in SQLite. Unknown/failed submissions count too, with no automatic retry. Counts reset at 00:00 UTC, include all configured gateways for that workspace and persist across restarts.
* Provider-reported input/output tokens are stored when available. They are not verified invoice amounts or a dollar spending cap. Daily request caps do not guarantee a particular monetary spend.
* Existing direct OpenAI, local Ollama, Meta and billing configurations are preserved. OpenAI embeddings currently remain a separate direct-OpenAI feature and are not sent through the gateway.

## Operator setup

First operate or select a legally usable, authenticated service that supports `/v1/responses` and the structured JSON schemas VYBE requires. This release does not install a gateway or authorize a new upstream provider. Do not expose its administrative console or master key to customers.

In the private server environment, set `TW_AI_GATEWAYS` to an object with one entry per approved gateway:

```json
{
  "budget": {
    "label": "Budget AI",
    "base_url": "https://YOUR_GATEWAY_HOST/v1",
    "models": ["YOUR_APPROVED_MODEL_ID"],
    "requests_per_day": 100
  }
}
```

The URL must use HTTPS on port 443 without credentials/query/fragment. Store no keys in this catalog. Restart the app after configuring it. An administrator can then open Settings → AI assistant connection → Use an AI gateway, choose an approved gateway/model, enter that workspace's scoped virtual key and explicitly enable real usage. The button is absent when no gateways are configured. Saving does not run a test or incur model charges.

`TW_AI_ENABLED` remains the platform-wide processing gate. Keep it and existing paid-usage permissions unchanged unless real usage is intended. The encrypted workspace enable flag is the explicit gateway usage approval.

## What is not enabled

No gateway endpoint or key has been configured in production. No inference, embedding or messaging test was sent. New API/Routerly billing administration, automatic virtual-key provisioning, currency billing reconciliation and live gateway compatibility remain separate work. Existing Razorpay subscriptions do not by themselves establish gateway usage-based billing.

Evolution's unofficial QR transport has not replaced the official Meta connection. It does not establish Meta Tech Provider approval and is not presented as an equivalent production WhatsApp Business Platform transport.
