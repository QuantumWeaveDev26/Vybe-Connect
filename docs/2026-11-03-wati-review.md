# WATI comparison and VYBE Connect improvements

## Evidence and scope

On 3 November, REA inspected the authorized WATI Astra page and captured its visible screen. Evidence: `ev_86e74f958fa49ccd9d6d72b60b31305d42c3cb20e510b19c91f10032d100ce27` (target discovery); the associated current page inspection and screenshot were reviewed in the session. This is surface evidence, not WATI source/backend equivalence. The main Astra content uses an external iframe; the same-origin accessibility capture cannot establish all of its internal workflows. No WATI account settings, agent configurations, billing or messages were changed.

The public VYBE deployment currently presents protected first-owner setup. An isolated local demo at port 8790 was created at the user's request, with a clearly named sample workspace, two paused sample AI agents and one disabled example webhook connection. Its database is outside the Git checkout. No production customer records were imported, no owner setup protection was removed, and no provider calls were made.

## Improvements implemented in this pass

- Search and status filters for AI and external-agent directories, with result counts and a no-match state. Configured dispatch is labelled separately from verified delivery.
- Duplicate an AI agent through an editable review form. Only name, instructions and proposal permissions are copied. IDs, schedules, execution history and archive state are not copied; saving creates a separate paused agent.
- Open activity scoped to a particular agent and return to all activity.
- Correct hosted developer/callback guidance and business-knowledge website-page descriptions.
- Add accessible AI close/navigation names and serve the new directory asset through the explicit static-route allowlist.
- Regression test every script and stylesheet linked from the entry page, alongside filtering, configuration-copy and renderer checks.

Browser checks in the isolated demo verified real account setup, agent creation, duplication, paused state, search/no-match counts and both directory status filters. The run buttons remain disabled without an AI connection. This does not verify inference, scheduling over time or messaging delivery.

## WATI capabilities and remaining gaps

| Area | VYBE implementation | Still required |
| --- | --- | --- |
| Astra surface | Search, agent cards, connection form, signed webhook events, reply-draft callbacks, delivery history, private feedback and help/tour | Full hosted agent builder, avatar/identity editing, channel deployment, deeper agent analytics and complete WATI workflow comparison |
| Workspace AI | Ask, private history, 12 preset configurations, manual and natural-language builder, model allowlist, background jobs, schedules, action permissions, reviewed findings | Live OpenAI quality/cost/cancellation acceptance; full tool vocabulary and comparable production agent behavior |
| Knowledge | Manual text, TXT/Markdown/CSV/DOCX indexing, one-page public website snapshots, passage references and usage reporting | PDF, full-site crawl, semantic retrieval and broader quality/evaluation tooling |
| Team inbox | Shared inbox, assignments, private notes/mentions, received media, drafts, takeover and team routing | Complete channel parity, calling, presence, SLA/business-hours coverage, browser/device media acceptance |
| Automations | Rules, graph drafts/publication/history, waits, no-response rules, sequences, contact actions and gated outbox delivery | Full WATI graph/trigger vocabulary and verified real-provider execution |
| Commerce and integrations | Selected adapters, products/orders, Shopify groundwork and webhook contracts | Complete live commerce mutations, payments/refunds, calling/media acceptance and wider integration catalog |
| Client services | Tenant-aware workspaces, memberships/invitations, optional MFA and recovery implementation | Public client onboarding, subscriptions/billing, complete granular access/SSO and deployed lifecycle acceptance |
| Deployment | Healthy isolated VPS container, persistent data, trusted HTTPS, authenticated API boundaries | Owner setup, real-provider verification, backup/restore drill, load/soak tests, alerts and operational sign-off |

The application is deployed, but full WATI parity and production-client clearance remain incomplete. These obligations are not replaced by adding API keys. The demo is a review environment; it does not assert working provider connections.
