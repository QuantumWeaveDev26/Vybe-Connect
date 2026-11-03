# External agents and developer webhook delivery

REA passive inspection on 29 October confirmed Custom Astra Agents, Connect your Agent, Build Astra AI Agents and the Name/Status/Event Types/Webhook URL/Last updated/Actions table (`ev_70ef7b687272cc41f330378cb9370f14503a5eba9b42f0fd49d51843c45d1eaa`). The creation form, event vocabulary, payload and callback protocol were not observed. Implement an independently documented event contract rather than claiming WATI backend equivalence.

Continue inline with TDD. Add an external-agent table and editable connection records. Configured connections receive tenant-scoped message.received and message.status events through a durable outbox, signed with server-only per-connection secrets. Dispatch is separately disabled by default; require exact HTTPS origin allowlisting, public DNS resolution, pinned TLS connections and no redirects. A failed or uncertain request is never automatically repeated. Explicit retries preserve the event identifier so receivers can deduplicate.

Agent callbacks require a fresh timestamp and valid HMAC, must reference the originating connector/contact/event, and create idempotent unsent reply drafts. They never send WhatsApp messages or mutate arbitrary contacts. Local setup and UI work without credentials. Keys and live verification remain deferred.

- [x] Test configuration, scope, outbox deduplication, signed payloads, network restrictions, uncertain outcomes and explicit retry.
- [x] Implement external_agents.py and hook inbound/status events transactionally; add a dedicated worker and signed callback endpoint.
- [x] Test callback freshness, guessed identifiers, body changes/replays and private reply-draft behavior.
- [x] Add REA-observed external-agent table columns, connection editor, delivery history and developer setup instructions.
- [x] Run local checks, update parity evidence, package and restart. No live network deliveries, paid services or WATI mutations during verification.

Release evidence: full suite 164 tests passed; Python compilation, JavaScript syntax and renderer checks passed. No live provider calls, webhook deliveries or paid usage occurred. Independent final review and current visual acceptance remain unavailable after the prior workspace credit limit. Exact parity remains incomplete.
