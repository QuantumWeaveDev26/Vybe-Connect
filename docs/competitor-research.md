# WATI replacement: feature research and implementation priorities

Researched 29 October 2026 from public official product/help pages. This compares three relevant alternatives, not an exhaustive ranking of the market. No competitor accounts were created, paid services invoked, or private competitor workflows verified. Capabilities below are documented product capabilities, not independently tested reliability claims.

The requested scope is the complete WATI-equivalent product, including AI, integrations and multi-business service delivery. WATI remains the observable workflow/layout reference. Competitor ideas supplement that scope; they do not replace it with a smaller dashboard.

| Reference | Documented strengths | Features worth building | Priority and current boundary |
|---|---|---|---|
| [respond.io AI agents](https://respond.io/help/ai-agents/getting-started-with-ai-agents) | Sales/support/receptionist agent templates; business knowledge; review and testing; assignment, conversation closure and lifecycle actions; human takeover | Configurable agents grounded in company information, isolated agent testing, explicit human takeover, approved internal actions | Strongest overall reference for AI-assisted team operations, based on our requirements. We have read-only local agents and workspace knowledge; customer-facing autonomous agents remain pending. Admin-reviewed local proposals and an explicit human takeover lifecycle are now implemented; see adopted-features.md |
| [respond.io workflow integration](https://roadmap.respond.io/changelog/ai-agent-can-now-trigger-workflows) | Agents can trigger existing structured workflows | Keep the language model separate from deterministic business actions; allow only configured actions with execution records | Pending. The current assistant has no write tools and cannot send customer messages |
| [SleekFlow AI](https://sleekflow.helpjuice.com/en_US/sleekflow_ai) | Knowledge management, smart reply, writing assistance, summaries, execution traces, agent optimization and human/AI conversation control | Knowledge source management, reply drafting with source references, traces and feedback, conversation summaries | First addition implemented: persistent, workspace-scoped text sources with admin editing and enable/disable. Source data is included in actual local model requests. No model runtime has been verified; source citations remain model behavior, not a deterministic guarantee |
| [SleekFlow flow builder](https://help.sleekflow.io/en_US/advanced-flow-builder) | Triggers for messages, contact changes, scheduled time, webhooks and commerce; round-robin assignment; business-hours examples | Availability-aware routing, round-robin assignment, event-based automation, scheduled follow-ups with cancellation and idempotency | Pending. Existing graph runner handles a bounded subset of conversation steps as drafts; it is not this full automation engine |
| [Interakt sales CRM](https://www.interakt.shop/sales-crm/) | Lead collection and owner assignment, follow-ups, visual sales pipeline, roles and tasks | Contact-linked deal stages, owner, follow-up tasks and a pipeline view; measurable conversions | Implemented: contact-linked deal stages, owners, follow-up tasks and pipeline view. Amounts are manual estimates, not payment/revenue attribution |
| [Interakt support](https://www.interakt.shop/customer-support-automation/) and [commerce](https://www.interakt.shop/) | Unified inbox, routing, customer context, bots, campaign/team reporting, catalog and commerce integrations | Agent availability, customer context alongside chats, catalog/order lookup and abandoned-checkout recovery | Pending provider adapters and real events. No connected Shopify store, checkout, payment, Instagram or RCS delivery is claimed |

## Recommendation

Use respond.io as the main feature reference for AI-assisted team operations, SleekFlow for grounded AI and automation controls, and Interakt for sales/commerce. This is an engineering judgement about this project's needs, not a claim that any one product is universally best or cheapest.

Delivery order:

1. Complete the WATI parity ledger and verify the core Meta onboarding, inbox, approved templates and outbound queue with the user's own test number.
2. Extend AI from the existing read-only assistant: company knowledge (text-source foundation now implemented), test conversations, summaries/draft replies, human handoff, then explicitly permitted actions with audit records.
3. Add sales pipeline and follow-up tasks without inventing sales figures.
4. Extend workflow events, routing, schedules and outbound integration jobs, with idempotency and failure visibility.
5. Add catalog/store adapters using a real connected store and verified test events.
6. Complete public multi-business onboarding, per-business credentials, production storage/queues, backups, billing and operational verification before commercial launch.

## Latest WATI/REA evidence

Fresh passive authenticated-page inspection: `ev_35512b0b9c95b7d5d71a26ebbd0f71124ae55e176a86ab8775d2471c1f78bc35`, 29 October 2026. Main campaign page, navigation and accessibility were observed. Capture is origin-filtered and attach-limited; it does not cover every feature or backend. REA's browser scenario provider still returns `execution_failure` after the browser was reopened. Wati AI Agents catalog was subsequently captured; see the expanded-catalog update below. This is partial product coverage, not an all-feature tour.

## Knowledge-source foundation delivered in this pass

- Admins can add, edit, disable and delete text sources. Members can read sources in their workspace.
- Up to eight sources per workspace, each with title and up to 4,000 characters of content. Content is stored in SQLite; no external crawler, embeddings service or paid API is used.
- Every new AI request receives currently enabled sources from the authenticated workspace. A source in another business cannot be read, changed, deleted or supplied to the model through guessed IDs.
- Source bodies are treated as untrusted reference data in the model instructions. Source citations and uncertainty are requested; actual answer quality still needs a running local model and evaluation.
- Existing chat history is retained after disabling/deleting sources. Earlier answers are not retroactively rewritten. This is a text-context foundation, not a document-ingestion/retrieval system.
- Automated suite: 34 tests pass. New tests verify persistence, source inclusion/exclusion, workspace boundaries, admin permissions and limits. Model responses in tests are controlled doubles; real AI generation and the latest UI visuals remain unverified.

## Expanded AI catalog captured on 29 October

REA passively captured the eleven suggested Wati AI agents after user-assisted navigation: ev_0647823ac00c402a6e763d2c22cc2fb62631cb133816e5b25d66aac28752b3d2. Astra integration controls were captured as ev_e9ce45c4b433a26aaebdba2e02b9d55c2d439f5155cb74502ede1e19adde426c. The older unresolved-catalog notes are historical. No Hire, Send, agent activation or account changes were performed.

TeamWave now offers independently written customizable presets for Inbox Triage, Re-engagement Scout, Urgency Watcher, Top Topics, Spam Watcher, Ready-to-Buy, Automation Health Check, Campaign Readiness Checker, Segment & Contact Checker, Campaign Idea Finder and Account Health Checker, plus Daily Digest. These save instructions for on-demand read-only analysis; they are not a reconstruction of WATI's agent backend.

AI requests receive up to 20 recent conversations (three messages per contact, 500 characters per message), enabled business knowledge, automation configuration, tag counts, a bounded queue summary and configuration flags. Scope limits and unavailable wallet/channel-health inputs are explicit. No background monitoring, automatic tagging/assignment, saved findings review workflow or customer messaging actions are implemented yet.

Full suite: 35 tests passed. Regression coverage includes actual conversation context with no outbound message or queue write, source persistence, enable/disable, deletion, limits, permissions and workspace isolation. Model responses in tests are controlled doubles. Real AI generation, live Meta operation and current UI visual verification remain pending.
