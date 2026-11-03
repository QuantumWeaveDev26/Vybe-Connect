# Customer-facing AI assistant

Ruling: prioritize customer-facing AI over persistent graph waits in this increment because the user clarified that services, agents and AI functionality matter most. Graph expansion remains a recorded gap; no graph changes have begun.

Continue inline with TDD. One configurable support assistant per workspace handles new real inbound messages that were not already consumed by a flow or keyword rule. Configuration can be drafted without keys. Enabled assistants enqueue only when the AI runtime is configured/approved. Default mode creates unsent drafts. Live mode additionally requires complete Meta settings, a live-send gate and a separate per-workspace AUTO_REPLY flag; activation is explicit and remains disabled in this development run.

Jobs persist, coalesce rapid inbound fragments, and use a separate worker. Input includes only the selected contact's real conversation and business knowledge, never private notes, other contacts or workspace diagnostics. Structured output can request human handoff. Human takeover, STOP, a changed conversation, policy/config edits or revoked runtime access suppress late publication. Live replies recheck the real 24-hour window immediately before one provider submission. Unknown model/send outcomes are never automatically retried. A vanished worker loses its lease; duplicate inbound webhooks cannot enqueue duplicate replies.

- [x] Write failing tests for grounded selected-contact context, draft-only operation, handoff, consent/STOP behavior, paid/live gates, stale results and duplicate/unknown outcomes.
- [x] Implement customer_assistant.py, provider schema/system support and transactional enqueue/worker hooks.
- [x] Add assistant configuration, mode controls, run history and conversation navigation.
- [x] Run local/domain/provider/HTTP/renderer checks, update parity boundaries, package and restart. Keys and live verification remain deferred; do not invoke paid providers or live WhatsApp sends during checks.
