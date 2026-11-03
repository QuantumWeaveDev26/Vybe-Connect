# WATI feature inventory and release boundaries

## Current verified increment — 29 October 2026

Chatbot media and template nodes now use the durable outbox, frozen resource/recipient snapshots, current consent and approval checks, attachment captions and correct template-versus-free-form window handling. See [rich chatbot delivery](docs/rich-chatbot-delivery.md). Live providers and exact WATI parity remain unverified.

Live chatbot text delivery is now implemented behind separate server approval, with durable one-at-a-time checkpoints, accepted-prompt question handling, acceptance-based waits, cancellation fences and unknown-result human review. Drafts remain the default; live provider verification is pending. See [live chatbot delivery](docs/live-chatbot-delivery.md).

2 November update: visual chatbots now set bounded custom attributes, remove tags and assign current workspace teammates, with execution-time access checks and atomic blocked-flow handling. See [chatbot contact actions](docs/chatbot-contact-actions.md). REA live browser access was unavailable; this update uses prior captures and local verification.



Customer no-response rules now support persistent accepted-reply watches, configurable waits, cancellation on real reply or human control, and once-only local evaluations. Rule saves exclude historical messages. See [no-response rules](docs/no-response-rules.md).

Background AI agents now have per-agent proposal permissions, information-only mode, generation-time validation, configuration-version fencing and permission/archive checks at approval. Pending proposals cannot bypass revoked actions. See [agent action permissions](docs/agent-action-permissions.md).

AI customer handoffs now support administrator-selected team pools and transactional least-busy routing, preserve existing assignees and record the selected workload snapshot. Removed members are ignored; no surviving pool falls back to the assistant administrator. Reviewed AI assignment also cancels pending automation continuations. See [AI team routing](docs/ai-team-routing.md).

Rules now also react to contact creation/updates, added or changed custom attributes and conversation open/solve transitions, with exact field filters and recent execution history. Duplicate/unchanged source events, recursive actions and human-held conversations are guarded. Customer no-response rules now use accepted-reply timers and once-only local evaluations. Exact WATI event semantics and call/social triggers remain pending.

The inbox now records received attachments, retrieves them explicitly through a restricted verified Meta download adapter, stores private local files and reuses completed downloads. Non-text messages pause automation for human review. Supported formats/size and live verification boundaries are documented in [received media](docs/received-media.md).

Analytics now queries recorded real traffic across the complete message database for inclusive UTC date ranges, with daily charts/tables and CSV export. Provider acceptance, recorded delivery/read and unknown outcomes remain distinct. Current workload is explicitly a present-time snapshot. See [message analytics](docs/message-analytics.md).

Team access now supports transactional admin/agent role changes and workspace removal, last-administrator protection, pending-invitation revocation and open-assignment cleanup. The UI clears cached workspace data after access denial. Other workspace memberships and history remain. See [member access](docs/member-access.md).

Team onboarding now has one-time expiring invitation links, hashed token storage, revocation, issuer-access checks and atomic acceptance. New recipients choose passwords; existing accounts must verify theirs. Links are shared manually and remain local until hosting is configured. See [team invitations](docs/team-invitations.md).

Rules now support optional saved-segment conditions, priority and ordered local actions for tags, assignment, status, text attributes, unsent drafts, internal tasks and human handoff. Dependency and contact-capacity checks precede all writes; legacy keyword-draft behavior is retained. External actions and other event triggers remain pending. See [rule actions](docs/rule-actions.md).

Chatbot graphs now support persistent wait nodes (1 second–7 days), restart-safe due times, transactional timer continuation, competing-worker protection and visible waiting state. STOP, takeover and saved flow settings cancel active sessions. Continuations create drafts; live graph sends and snapshot-preserving published versions remain pending. See [chatbot waits](docs/chatbot-waits.md).

Website knowledge now supports explicit public HTTPS page ingestion, review before enablement, manual refresh, private-address blocking and atomic passage replacement. Failed refreshes retain the last successful snapshot. Sources use the same local lexical retrieval and customer-source approval controls. Full-site crawling, scheduled refresh and semantic search remain pending. See [website knowledge](docs/website-knowledge.md).

AI handoffs now preserve valid assignments, route to a configured workspace teammate or administrator fallback, optionally create one internal follow-up task per job and record the handoff reason in the inbox. Resume resolves the handoff without replaying stopped work. Online presence, capacity limits and SLA routing remain pending; optional team-pool workload balancing is implemented.

Customer AI can now use up to five explicitly verified linked Shopify order snapshots, with separate administrator opt-in, current-shop and 24-hour freshness checks, projected order facts and stale-result suppression. Commerce provides ownership link/unlink controls. These are synced snapshots, not live customer lookups; order mutations remain unimplemented.

Customer support AI now handles unmatched real inbound messages with approved knowledge, durable jobs, daily request limits, unsent draft mode, human handoff and separately gated automatic WhatsApp replies. Stale context, STOP, staff takeover and uncertain outcomes are guarded. Settings are available before keys; live inference, delivery and model quality remain unverified. See [customer assistant](docs/customer-assistant.md).

External agents now have the REA-observed table layout, configuration, signed message-event outbox, delivery history, explicit retries and scoped reply-draft callbacks. Dispatch requires a server gate, public HTTPS allowlist and secret; it remains disabled by default. The independent payload/callback contract is documented in docs/external-agents.md; WATI private protocol equivalence remains unverified.

Contact segments now support saved typed all/any conditions, visual editing, local audience preview and dynamic campaign targeting. Consent remains required. Deleting a segment blocks launch rather than widening the audience. Conversation-filter sharing/unread controls and complete WATI operator/dialog parity remain pending.


Document knowledge now supports local TXT/MD/CSV/DOCX extraction, up to 20 files, bounded lexical retrieval and validated OpenAI passage links. Sources can be disabled or deleted. PDF extraction, full-site crawling, semantic/vector retrieval and equivalent WATI training controls remain pending.

Sequences now have up to eight ordered template steps, persistent relative waits, explicit reviewed launch, pause/resume/cancel, consent rechecks, stable launch identifiers and failure propagation. Drafting is available before credentials; real launch requires complete Meta configuration, live sending and approved templates. Existing runs retain snapshots when definitions are edited. Delivery/read remains provider-webhook evidence, separate from acceptance.

Durable private AI chat jobs now support append queues, truthful progress, provider-aware cancellation, answer feedback, validated message sources and server-allowlisted model selection. REA-captured loaded frontend evidence established the two WATI mode choices, Create an agent and Get insights, and the 8,000-character prompt limit. The mode labels and limit are implemented. Natural-language agent creation now generates an editable proposal, supports follow-up refinement and installs a paused review-first agent after administrator approval. Exact WATI internal creation, authorization and tool behavior remain unverified.

The new attachment workflow uploads to Meta, stores workspace-private files, reviews a caption/recipient and sends once with a stable request identifier. Uncertain sends are never retried automatically. Real inbound 24-hour eligibility and live-send configuration are required. Read-only Shopify product/order sync has actual pagination, workspace-specific credentials, and signed deduplicated webhook receipts; webhook receipts require explicit read sync before catalog changes.

**298 Python tests passed in the full suite**; Python compilation, JavaScript syntax and renderer/privacy checks passed. All provider transports were mocked during automated checks. No live OpenAI inference, Meta uploads/sends, Shopify reads, purchases or deployments were performed. Visual parity and production readiness remain unverified. Exact WATI parity remains incomplete. See [current verification](docs/current-verification.md) and [acceptance ledger](docs/wati-ai-parity-checklist.json).

29 October update: full product parity, including AI and integrations, remains the user's target. Added persistent workspace business knowledge for the local AI assistant (admin source CRUD, enable/disable, tenant-scoped context). Text sources and document retrieval are now implemented. Customer-facing support drafts and guarded automatic replies are locally implemented. Full-site crawling/PDF ingestion, autonomous AI actions and live model verification remain pending. [Competitor research and build priorities](docs/competitor-research.md).

Current increment: sales pipeline, follow-up tasks, structured on-demand AI findings, administrator action review and human takeover are implemented. See [adopted feature scope](docs/adopted-features.md). Historical update notes below describe earlier milestones; the current increment supersedes their references to findings/CRM/takeover being pending.

Inspection date: 28 October 2026. Target: user's authenticated WATI workspace. Browser screens and REA captures were used; backend source, provider internals and unrestricted feature parity were not established. No messages, campaign publishes, purchases or template submissions were performed.

| Area | Observed in WATI | TeamWave first local pilot |
|---|---|---|
| Navigation | Campaigns, Inbox, Contacts, Astra, Automations, Commerce, Ads, Analytics, Connectors, Developers, Settings | Familiar grouping, independent branding |
| Campaign overview | Date range, delivery states, unique-contact limits, quality, calendar/list planner, CSV export | Recorded counts, calendar/list drafts, actual outbound queue; no invented Meta quality/limits |
| Campaign wizard | Name, single-send/drip, approved template, CSV/segments/manual selection, filters, scheduling, retries, SMS fallback, contact updates | Template/tag audience, opt-in checks, timezone-aware queue scheduling and cancellation, no automatic uncertain retry; persistent drip execution is implemented separately; saved contact segments are now implemented; full conversation filtering, custom retry policies and SMS remain pending |
| Templates | Categories/languages/status, import/export, edit/copy/delete, Meta submission | Local drafts, category/language, variable preview, real Meta text-template submission and approval sync; provider live verification pending |
| Template content | Standard, catalog, carousel, limited offer; text/image/video/document headers; body variables/formatting; footer; website, copy code, voice call, contact info, quick reply and Flow buttons | Full-page text-template editor with text header/footer, name variable, quick reply/static HTTPS/phone buttons and live preview; media, carousel, offer-code and WhatsApp Flow buttons remain pending |
| Inbox | Filters, channels, chat/groups, search, favorites, assignment/status, notes, templates, replies, attachments/voice/emoji/stickers, customer panels | Persistent text inbox, internal notes, assignment/status, reusable replies, contact profile; manual gated Cloud API text adapter |
| Inbox extra tabs | Conversation summary, inbox automations, call records; download chat; spam/block | Selected-conversation AI context and outbound attachments implemented; received downloads are implemented with bounded restricted Meta retrieval; calls, groups and full inbox extra-tab parity remain pending |
| Contacts | Import/export, overwrite/skip policies, tags, attributes, source, BSUID/phone, pagination | Create/edit, quoted CSV import with duplicate reporting, safe CSV export, tags/attributes, consent |
| Segments | Segment tab, create segment and membership management | Typed saved all/any contact segments, visual conditions, previews and dynamic campaign targeting; conversation filters and full WATI operator parity pending |
| Rules | Event triggers, filters, ordered execution, enable/disable, execution counts, clone/delete | Keyword/contact/attribute/conversation/no-response events, saved-segment matching, priority, ordered local actions, enable/disable and execution history; call/social triggers remain pending |
| Rule triggers | WhatsApp message/calls, changed/new contact attributes, customer no-response, Instagram events, TikTok message | WhatsApp keyword, contact, attribute, conversation status and accepted-reply no-response triggers; calls/social pending |
| Rule actions | Template/message, route chat, chatbot, AI agent, catalog, contact attribute, sequence | Ordered drafts, tags, assignment, status, text attributes, internal tasks and handoff; live sends, chatbot/AI/sequence invocation and catalogue actions remain pending |
| Visual chatbot | Existing flow inspected: connected node canvas, start node, questions/variables/choices, conditions, media messages, AI, subscribe/unsubscribe, attributes/tags, assignment, nested bots, status, template, delay, WhatsApp Flow, webhook, Google Spreadsheet, catalog/product; minimap/zoom, logs, performance, history, import/export, testing | Editable draggable graph with keyword trigger, message drafts, questions/answers, attribute conditions, tags, status and human handoff; graph validation and TeamWave JSON import/export; Persistent wait nodes and version-based cancellation implemented; AI/integration nodes, published snapshots, live graph sends, run history and performance remain pending |
| Reusable replies | Text, document, image, video, sticker, bot, sequence, attributes, templates and catalog | Reusable text replies |
| Sequences/drip | Creation, schedule, duration, reusable sequence and drip definitions | Up to eight template steps, snapshot runs, relative waits, consent checks, pause/resume/cancel and failure propagation over the durable queue; live-provider acceptance pending |
| WhatsApp Flows | Number selector; name, triggered/completed, dates, status/category; create | Provider publishing pending |
| Routing | Notify, assign user, assign team, reusable definitions | Direct inbox assignment plus configured AI handoff routing, existing-assignee preservation and optional internal tasks; teams, online availability and round-robin remain pending |
| Analytics | Inbox, sales, calling, chatbot, CX/topic/operator insight areas; period, ticket status, operator metrics, response/resolution times, tags, message types, delivery states, scheduled reports | Counts/charts derived from local messages and tickets; no synthetic provider receipts |
| Team | Users, teams, connect AI agents, roles/status, contact details | Admin/agent memberships and hashed one-time invitation links; email delivery, granular roles and production client signup remain pending |
| Commerce | Meta catalogue setup, Sheets/Shopify setup guidance, catalogue messages and checkout FAQ | Read-only Shopify product/order sync, signed receipts and explicitly verified order context for customer AI; catalogue messages and checkout mutations remain pending |
| Ads | Purchase add-on gate observed; not activated | Pending; no ad account changes |
| Astra | Agent table, status, event types, webhook URL, connect/build controls | AI Ask/Agents panel with local Ollama adapter, saved agent instructions and private user chat histories; live model not connected; independent signed external-agent event/draft callbacks implemented; full tool coverage and exact Astra protocol remain unverified |
| Connectors | API, integrations and webhooks navigation | Signed inbound webhook endpoint and environment diagnostics; broader integrations pending |
| Settings | Channels, user management, account details | Local users/workspaces, diagnostics and setup instructions |
| Multi-business SaaS | User requested internal use plus services to clients; platform internals not observed | Workspace isolation in local database; public SaaS onboarding, billing, hosting, backups and hardening pending |

REA evidence: authenticated capture `ev_f9283082f2b07f3cbe4c83f1b966d9ba25ccce6472cdb6e90808e6bc08a740fa`; script export `ev_b4c2ba1addb1a24af7eeae0ead3a39991da6bfdae920742b0473a1b51f32dbcf`; desktop screenshot `ev_5a33e2c8112458d783874fcf734d81228a62c5d1597b10b593c8a9c85e22e75e`. REA script analysis was partial due to its source deadline; script capture/export does not prove that every module executed. Captured third-party scripts and private account data stay in internal work files and are excluded from the application ZIP.

## AI panel and live integrations update
REA observed the WATI AI toolbar button and page-dependent prompt. Browser inspection exposed its embedded Ask/Agents panel, new-chat/history navigation, context chip, suggested campaign questions and mode picker. The Agents tab failed browser-control interaction and its inner catalog remains unverified. TeamWave now includes an analogous panel and real local AI adapter, not simulated answers. AI runtime configuration and live verification remain outstanding.

Real template operations and a persistent outbound campaign worker are now implemented. Automated transport tests verify request URLs and payloads using controlled responses; they do not establish successful operation with Meta.

## Latest REA pass
Authenticated workspace recaptured as ev_c8a071c4bb3102135642e12eeb35e37a4972c51e3de2b538c0c4f0398088aee0. Focused inert analysis of RouteOrchestrator and flow runtime modules retained parent ev_230402200e4e4abf85338fc006edf1d67a07845b1253c825e39e198f51e1fd5e, with explicit semantic retention limits. Automated navigation continues to fail in the REA provider; the selected-page screenshot hit its response deadline. This is not evidence of full parity.

## Expanded AI catalog captured on 29 October

REA passively captured the eleven suggested Wati AI agents after user-assisted navigation: ev_0647823ac00c402a6e763d2c22cc2fb62631cb133816e5b25d66aac28752b3d2. Astra integration controls were captured as ev_e9ce45c4b433a26aaebdba2e02b9d55c2d439f5155cb74502ede1e19adde426c. The older unresolved-catalog notes are historical. No Hire, Send, agent activation or account changes were performed.

TeamWave now offers independently written customizable presets for Inbox Triage, Re-engagement Scout, Urgency Watcher, Top Topics, Spam Watcher, Ready-to-Buy, Automation Health Check, Campaign Readiness Checker, Segment & Contact Checker, Campaign Idea Finder and Account Health Checker, plus Daily Digest. These save instructions for on-demand read-only analysis; they are not a reconstruction of WATI's agent backend.

AI requests receive up to 20 recent conversations (three messages per contact, 500 characters per message), enabled business knowledge, automation configuration, tag counts, a bounded queue summary and configuration flags. Scope limits and unavailable wallet/channel-health inputs are explicit. No background monitoring, automatic tagging/assignment, saved findings review workflow or customer messaging actions are implemented yet.

Full suite: 35 tests passed. Regression coverage includes actual conversation context with no outbound message or queue write, source persistence, enable/disable, deletion, limits, permissions and workspace isolation. Model responses in tests are controlled doubles. Real AI generation, live Meta operation and current UI visual verification remain pending.
