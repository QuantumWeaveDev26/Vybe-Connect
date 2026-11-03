# VYBE Connect - business messaging workspace

## Current verified increment — 29 October 2026

Team management now supports expiring availability, capacity-aware routing, assignment history and private comments with teammate mention notifications. See [team operations](docs/team-operations.md).

Account password changes now verify current credentials, revoke all account sessions and fence old-password login races. Offline server-operator recovery uses hidden interactive input and cannot create an account/database silently. Optional authenticator MFA now includes verified enrollment, replay protection, account-wide session revocation, single-use recovery codes and invitation enforcement. Email recovery and deployed/device acceptance remain pending. See [account security](docs/account-security.md).

Deployment groundwork now includes explicit HTTPS origin/Host checks, Secure production cookies, protected fresh setup, coarse health/readiness endpoints, non-root container/proxy configuration and offline private-data backup/restore. Docker/TLS and full production readiness remain unverified. See [deployment gates](DEPLOYMENT.md) and [competitor adoption](docs/competitor-adoption.md).

Chatbot media and template nodes now use the durable outbox, frozen resource/recipient snapshots, current consent and approval checks, attachment captions and correct template-versus-free-form window handling. See [rich chatbot delivery](docs/rich-chatbot-delivery.md). Live providers and exact WATI parity remain unverified.

Live chatbot text delivery is now implemented behind separate server approval, with durable one-at-a-time checkpoints, accepted-prompt question handling, acceptance-based waits, cancellation fences and unknown-result human review. Drafts remain the default; live provider verification is pending. See [live chatbot delivery](docs/live-chatbot-delivery.md).

2 November update: visual chatbots now set bounded custom attributes, remove tags and assign current workspace teammates, with execution-time access checks and atomic blocked-flow handling. See [chatbot contact actions](docs/chatbot-contact-actions.md). REA live browser access was unavailable; this update uses prior captures and local verification.



Background AI agents now have per-agent proposal permissions, information-only mode, generation-time validation, configuration-version fencing and permission/archive checks at approval. Pending proposals cannot bypass revoked actions. See [agent action permissions](docs/agent-action-permissions.md).

AI customer handoffs now support administrator-selected team pools and transactional least-busy routing, preserve existing assignees and record the selected workload snapshot. Removed members are ignored; no surviving pool falls back to the assistant administrator. Reviewed AI assignment also cancels pending automation continuations. See [AI team routing](docs/ai-team-routing.md).

Rules now also react to contact creation/updates, added or changed custom attributes and conversation open/solve transitions, with exact field filters and recent execution history. Duplicate/unchanged source events, recursive actions and human-held conversations are guarded. Accepted-reply no-response timers are implemented; exact WATI semantics and call/social triggers remain pending.

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


A working local pilot inspired by the WATI workflows inspected in your account using browser control and REA. You own this application source. The package contains independently written implementation code, not WATI's captured scripts or your WATI customer data.

**This is not complete WATI parity or a production SaaS ready for clients.** See PARITY.md for inspected features, current coverage and remaining work.

## Earlier AI milestone — 29 October 2026 (historical)

Background schedules, pause/resume, agent edit/archive/restore, activity history, private agent-bound chats, selected-conversation context and the OpenAI Responses adapter are implemented. All eleven observed role presets plus Daily Digest are present. Keys stay server-side; OpenAI paid calls require a separate per-workspace approval flag. No paid calls were performed.

That earlier milestone passed 66 Python tests. The current release results and scope are recorded above; visual parity, exact agent activation/review behavior, backend equivalence and live provider execution remain unverified. See [AI release scope](docs/background-ai-release.md) and [acceptance ledger](docs/wati-ai-parity-checklist.json).

## Run on Windows

1. Extract the ZIP into a folder you control.
2. Ensure Python 3.13 or newer is installed. No pip/npm install is needed.
3. Double-click **START.cmd**. Keep its terminal window open.
4. Open **http://127.0.0.1:8787** in your browser.
5. Create your business and owner account. Use a unique password of at least 12 characters. There is no shipped default account or password.
6. Add your actual contacts and configure your own providers. Sample loading and simulated sends are hidden and disabled unless TW_SANDBOX=true is explicitly set for a separate test database.

PowerShell alternative, from the extracted `teamwave` folder:

```powershell
python server.py
```

Stop using Ctrl+C in that PowerShell/terminal window. If the port is already in use, run `python server.py --port 8790`, then open http://127.0.0.1:8790.

## Latest feature update

Sales pipeline, follow-up tasks, AI findings with administrator review, and human takeover are implemented. See [adopted features and verification](docs/adopted-features.md). AI requires a configured local model; full WATI parity and real-provider verification remain pending.

## What works locally

- Workspace-scoped accounts and data; multiple businesses, admin/agent roles, local team account creation and workspace switching.
- Shared persistent text inbox, operator assignment, open/pending/solved states, private notes, contact profiles, quick replies and template text insertion. Sessions sharing this server refresh periodically.
- Contacts, tags, custom JSON attributes, explicit marketing consent, quoted CSV import with row errors/duplicate reporting, and formula-safe CSV export.
- Template drafts, category/language, text preview, real Meta submission and sync of provider approval states. Text-body sending supports a single name parameter; rich templates remain pending.
- Campaign drafts, tag audiences, opt-in enforcement, calendar/list planner, real scheduled outbound queue and explicit launch/cancel operations. Approved text templates are required. Provider acceptance is distinct from delivered/read receipts.
- Keyword rules, visual chatbot editor with draggable nodes and connections, message drafts, questions that save answers, conditions, tags, ticket status changes, and human handoff. Graph JSON import/export uses TeamWave format. Missing edges and cycles are validated on save. The next simulated/real inbound event advances a waiting question, even though its question was only drafted; use this engine for local testing until live automation approval/delivery is implemented.
- Saved reusable replies and sequence definitions. Sequence timing is documentation/configuration only: there is no background sending worker.
- Local activity charts, ticket counts, operator workload, audit log, Meta diagnostics and a real AI adapter with Ask/Agents panel and private chat histories. Read CONNECTIONS.md for runtime configuration.
- Official Cloud API manual text-send adapter, inbound webhook verification/HMAC checking, message deduplication and delivery update handling. Live code paths have **not** been tested against Meta. They stay disabled unless you explicitly configure and enable them.

## Meta setup comes later

An existing Meta account is useful, but connecting also needs the WhatsApp Business account, phone number ID, app access token, app secret, verification token, API version, webhook subscription and a publicly reachable HTTPS callback.

The Meta Connection screen displays the exact environment names for each business workspace. Copy `.env.example` to `.env`, use those names, and restart the server after changes. Credentials are read server-side and never returned to the browser. Keep `.env` outside shared source bundles.

Default: live sending and sandbox operations are disabled. AI calls require an explicitly configured local runtime. Live campaigns use the persistent queue only when the workspace LIVE environment gate is enabled. Live manual free-form replies require a real inbound webhook within 24 hours; simulated incoming messages cannot open this window. Accepted API requests are not labeled delivered. An uncertain send result is recorded as unknown with no automatic retry.

The local server accepts only loopback Host headers and binds to 127.0.0.1. It is intentionally **not** a production deployment target or configured reverse-proxy service. Do not expose it to clients or simply open a public firewall port. Hosting, HTTPS, production identity/recovery, encrypted credential management, durable queues, backups, monitoring and a security review are required before providing a hosted service.

## Data and limits

The default database is `data/teamwave.db`, created on first run. It contains your contacts, chats and account password hashes. Back it up while the server is stopped; protect local disk access. Sessions expire after 12 hours. Forgotten-password recovery currently requires the offline server-operator procedure in docs/account-security.md; self-service email reset remains pending.

The inbox displays the latest 2,000 workspace messages; date-range traffic analytics query the complete local database, while workload uses current contact states. Imports accept up to 5,000 rows/1 MB per request. Browser drafts and unsaved graph edits should be saved before navigating away. Workspace-level isolation and two roles are implemented; granular team queues, public signup/embedded onboarding, billing, complete media/template coverage, calls, unrestricted AI tools, catalogue/ads integrations, WhatsApp Flow publishing, version history, scheduled reports and production queue orchestration are still pending.

## Verify

From the extracted folder, in PowerShell:

```powershell
python -m unittest discover -s tests -v
```

The tests use temporary databases and do not call paid providers. Browser QA used a separate synthetic database outside this source folder; no real WhatsApp message or payment was sent. See VERIFICATION.md for tested workflows.

## Source map

- `store.py`: authentication, workspace boundaries, persistent domain operations.
- `flows.py`: validated local flow graphs and bounded interpretation.
- `meta.py`: server-side official WhatsApp Cloud API adapter and HMAC helpers.
- `server.py`: loopback HTTP/API/webhook boundary.
- `static/`: browser UI, SVG icons, flow canvas and responsive CSS.
- `tests/`: domain and HTTP regression tests.

REA captures are retained separately as internal investigation artifacts. They are not included in this deliverable.

## Current connection status

See CONNECTIONS.md for real Meta and AI setup. No live provider connection has been verified. The current release is not a complete pin-to-pin WATI clone. The source provides an implementation foundation, not a claim of service readiness.


## Product name and compatibility

The product is now VYBE Connect (previously TeamWave). Existing TW_* environment variables, database filenames and X-TeamWave-* webhook signature headers remain compatible. Credentials and private data are not included in this repository. Run `python server.py --port 8788` for local use; see DEPLOYMENT.md for the separate production gates. Source and test checks do not establish full WATI parity or production clearance.

The local UI now exposes Astra / Custom AI, card-based agent connections, the neutral workspace theme, a help launcher, guided walkthrough and a private workspace feedback inbox. No account-specific WATI agent, customer content, payment warning or support-service credentials are copied into the app. Its signed agent protocol is independently implemented; it is not WATI's proprietary backend.
