# External agents and signed webhooks

REA observed the authenticated WATI Custom Astra Agents table and its connection/build actions on 29 October 2026 (`ev_70ef7b687272cc41f330378cb9370f14503a5eba9b42f0fd49d51843c45d1eaa`). The local Custom AI Agents screen implements the observed columns: Name, Status, Event Types, Webhook URL, Last updated and Actions. Creation forms, private payload formats and WATI callback behavior were not observed. The following protocol belongs to this independent application.

## Configure after building

Create a connection locally, then choose Connection setup for exact variable names and the callback path. Credentials remain in the server's .env file. For example, using uppercase IDs only in environment variable names:

```
TW_WEBHOOK_WORKSPACE_ID_ENABLED=false
TW_WEBHOOK_WORKSPACE_ID_ALLOWED_ORIGINS=https://your-agent.example
TW_WEBHOOK_WORKSPACE_ID_CONNECTION_ID_SECRET=ENTER_LOCALLY
```

The connection must also be enabled in the UI. Keep dispatch false until external delivery is approved. No events are queued while dispatch is disabled or the endpoint/secret is unconfigured. Enabling later does not replay earlier customer messages. No actual network requests occur while saving a connection or showing configuration status.

Only HTTPS port 443 is supported. URL credentials, query strings, fragments and private IP destinations are rejected. Exact origins must be allowlisted. All resolved addresses must be public; the transport pins a resolved address while verifying TLS for the original hostname. No redirects or environment proxies are used.

## Event request

Version 1 envelopes contain id, version, type, workspace_id, connector_id, created and data. Supported event types:

- message.received: contact_id and message with id, body, direction and ts. Simulated inbound messages and conversations under human takeover do not trigger agent events.
- message.status: message_id, provider_id and status. Unknown provider IDs and repeated status notifications do not create duplicate events.

Headers are X-TeamWave-Event-ID, X-TeamWave-Timestamp and X-TeamWave-Signature. The signature is `sha256=` plus the lowercase hex HMAC-SHA256 of `timestamp + '.' + raw_body`, using the connection secret. Verify against the exact raw bytes; do not reserialize first. Check timestamp freshness and deduplicate event IDs before external actions.

An HTTP 2xx response records a delivered webhook, which establishes receiver acknowledgment only. Other responses are failed; timeouts and interrupted workers are unknown. Neither outcome is automatically retried. Explicit retries retain the event ID and can duplicate receiver side effects unless it deduplicates. The UI asks for review. Connection changes cancel unsent events; in-flight requests may already have reached the previous receiver.

## Reply callback

POST a signed JSON object to the exact /agent-callback/<workspace>/<connection> path shown in setup:

```json
{"event_id":"EVENT_ID","reply_id":"UNIQUE_REPLY_ID","body":"Suggested reply text"}
```

Use the same signing scheme and a timestamp within five minutes. The event must belong to that connection, still target its current URL and refer to an inbound customer message. The server derives the recipient from the stored event; callers cannot select another contact. Reusing a reply_id with the same raw body returns the existing draft; changing its body is rejected. Human takeover and disabled connections block callbacks.

Callbacks create unsent reply drafts. They never send WhatsApp messages, grant consent, charge customers or mutate arbitrary records. A teammate reviews and sends through the existing inbox controls. Autonomous third-party agent action parity remains incomplete.

## Limits and evidence

Up to 20 connections per workspace, 1,000 pending deliveries per workspace and 100 recent event summaries in state. Queue overflow writes webhook.outbox.full to the audit log; incoming customer messages remain stored. Operators must reconcile overflow manually. The application remains a loopback local pilot; public HTTPS deployment, retention/cleanup operations and client onboarding remain pending.

Local tests cover HMAC signatures, freshness, event/tenant scope, human takeover, idempotent drafts, URL changes, removed subscriptions, public-address checks, pinned transport/no redirects, role restrictions and real local HTTP callbacks. Provider transports are mocked. Live endpoints, WATI private protocol equivalence and exact rendered visual parity remain unverified.
