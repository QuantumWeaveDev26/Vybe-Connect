# Customer support AI

One support assistant per workspace handles new real inbound text messages left unmatched by existing rules or chatbots. Configure it under Automations → AI Customer Replies. Select only sources approved for customer-facing use. Settings can be saved before credentials exist; missing runtime access prevents job creation rather than replaying old messages later.

Draft mode creates unsent replies for team review. Live mode additionally requires complete Meta configuration, its LIVE flag and TW_AI_<UPPERCASE_WORKSPACE_ID>_AUTO_REPLY=true. OpenAI requires its server-side key, enabled runtime and workspace ALLOW_PAID flag in both modes. All flags remain disabled in the development configuration. Keys belong in the local server .env, never the browser or source archive.

Context contains at most twenty real messages from the selected conversation and explicitly approved business knowledge. It excludes private notes, simulations, unsent drafts and other contacts. Uploaded documents use bounded local lexical retrieval; this is not vector search. Strict structured output validates supplied document/chunk identifiers. Source validation does not independently prove model statements are correct.

Jobs persist in SQLite, coalesce queued customer fragments and count submitted model attempts against a per-workspace daily limit from UTC midnight. Missing knowledge or exhausted daily allowance causes local human handoff without a model call. Model-request or output failures require human review. A handoff marks the conversation Pending and holds automation; any suggested customer response stays an unsent draft.

STOP, staff takeover, policy edits, assistant edits, newer real messages, staff replies, revoked runtime access and expired service windows suppress stale work. Local Stop fences the result; an already submitted model request may continue and cost money. A WhatsApp submission already in flight cannot be recalled. Unknown model/send outcomes and expired worker leases are recorded without automatic retry. Reconcile unknown outcomes before resending.

This is an independent implementation, not WATI's private AI runtime. Equivalent hiring lifecycle, all WATI agent tools, semantic training, calls, production scaling and real provider acceptance remain incomplete. Local checks mock provider transports and do not establish live delivery or answer quality.

## Verified customer order context

Commerce → Customer order access lets an administrator link a synced order to a contact after verifying ownership. A link cannot silently move to another contact; unlink it first. Order numbers typed in messages never establish ownership. The assistant's separate “Allow verified linked Shopify order snapshots” setting defaults to off.

When enabled, context includes up to five linked orders from the currently configured shop, synced less than 24 hours ago. Only order name, financial/fulfillment status, total and last-sync timestamp are projected. It excludes Shopify IDs, addresses, emails, phones and private fields. The assistant is instructed to identify the last-sync time; cached status is not a live lookup. Missing/stale records require human help and do not prove that the customer has no orders. Order changes, expired snapshots or removed links suppress a pending answer before publication. No provider reads are triggered by customer messages. Sync still uses the authenticated Shopify connector; no refunds, payments or fulfillment changes are implemented.

## Handoff routing

The assistant configuration can select a workspace teammate and optionally create an internal follow-up task. Existing valid conversation assignments take priority; otherwise the selected teammate receives the chat. If that member loses workspace access, routing falls back to the assistant administrator. This is a membership check, not an online-presence or workload scheduler.

Explicit AI handoffs, invalid model output, uncertain WhatsApp submissions and eligible interrupted-worker recovery share the same transaction: Pending status, automation hold, internal reason and assignment. Follow-up tasks are local records, created once per job; they do not send emails or WhatsApp notifications. A staff-answered conversation is not reopened merely because an old generation lease expired. Uncertain sends still require provider reconciliation.

The inbox shows the handoff reason and creation time. Resume automation marks the handoff resolved and retains its history. It neither closes the follow-up task nor replays stopped jobs; the team manages task completion separately. These controls do not establish complete WATI routing parity, online availability, round-robin assignment, SLAs or notification delivery.
