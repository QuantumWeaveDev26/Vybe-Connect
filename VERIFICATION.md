# Current verification — 29 October 2026

See [current verification](docs/current-verification.md) for the latest release. Historical evidence below applies only to its dated build; it does not verify the current UI in a browser.

# Verification — 28 October 2026

Completed locally with Python 3.13.2 and a separate synthetic QA database. No Meta messages, AI API calls, payments, WATI publishes or account configuration changes were used for validation.

## Automated evidence

`python -m unittest discover -s tests -v` passed 31 tests:

- Password login, session revocation and setup lockout.
- Workspace data isolation, guessed cross-workspace IDs and membership checks.
- Agent restrictions on administration and automation.
- Quoted CSV imports, duplicate reporting and invalid phone rows.
- Campaign consent targeting, explicitly simulated messages and duplicate-run rejection.
- STOP opt-out handling.
- Duplicate inbound event suppression and keyword drafts.
- Service-window rejection before any provider network call.
- Persistent notes and operator assignment.
- Question/answer flow resumption, conditions, saved attributes, tags and human handoff.
- Rejection of circular and broken flow graphs.
- Formula-safe CSV export.
- Valid/invalid HMAC checks, cross-origin rejection, Host validation, session cookies, secret-file protection and unsigned webhook rejection.

JavaScript syntax and Python compilation were also checked.

## Browser evidence

Verified in the in-app browser against http://127.0.0.1:8788:

- First-run owner setup and authenticated dashboard.
- Loading only synthetic sample contacts and templates.
- Campaign confirmation and persistence of two simulated outbound messages; no delivered/read counts invented.
- Private note persistence and keyword-generated reply draft.
- CSV import of a quoted contact name with an invalid row reported separately.
- Creating a second business workspace and observing zero contacts from the first workspace.
- Creating a visual flow, adding/configuring a question, connecting it to handoff, changing its start node and saving it.
- Desktop dashboard visual inspection. Responsive CSS was observed in the default narrow panel as well.

## Not verified

Real Meta connection, outbound delivery, webhook delivery from Meta, approved-template submission, real users across devices, public hosting, commercial client onboarding, production resilience, attachments, AI or complete WATI feature parity.

The local pilot remains bound to 127.0.0.1. Read README.md and PARITY.md before using real customer data or planning public deployment.

## Subsequent implementation checks
- 28 tests pass after adding Meta request-contract tests, persistent queue/provider-state handling, opt-out rechecking, AI configuration errors and per-user AI history isolation. Provider/AI responses in these tests are controlled test doubles, not live provider verification.
- JavaScript syntax checks cover app, graph, assistant and shell files; Python sources compile.
- Updated static assets and bootstrap return HTTP 200 locally.
- Browser control became disabled in Work settings. The latest assistant panel and contextual-layout update have not received browser visual verification. Earlier screenshots show the earlier QA build, not proof of the final layout.

Latest change: full suite passed 31 tests after text-header/footer/button template support. Full-page editor JavaScript passes syntax checking. The new editor has not yet received real-browser visual verification.

29 October 2026: full suite passes 34 tests after adding business knowledge sources. Persistence, tenant isolation, admin-only changes, enabled-source context, deletion and limits are covered. AI test responses are controlled doubles, not real local-model generation. Knowledge UI JavaScript passes syntax checking; browser visual verification remains pending. See docs/competitor-research.md for source links and implementation priorities.

## Expanded AI catalog captured on 29 October

REA passively captured the eleven suggested Wati AI agents after user-assisted navigation: ev_0647823ac00c402a6e763d2c22cc2fb62631cb133816e5b25d66aac28752b3d2. Astra integration controls were captured as ev_e9ce45c4b433a26aaebdba2e02b9d55c2d439f5155cb74502ede1e19adde426c. The older unresolved-catalog notes are historical. No Hire, Send, agent activation or account changes were performed.

TeamWave now offers independently written customizable presets for Inbox Triage, Re-engagement Scout, Urgency Watcher, Top Topics, Spam Watcher, Ready-to-Buy, Automation Health Check, Campaign Readiness Checker, Segment & Contact Checker, Campaign Idea Finder and Account Health Checker, plus Daily Digest. These save instructions for on-demand read-only analysis; they are not a reconstruction of WATI's agent backend.

AI requests receive up to 20 recent conversations (three messages per contact, 500 characters per message), enabled business knowledge, automation configuration, tag counts, a bounded queue summary and configuration flags. Scope limits and unavailable wallet/channel-health inputs are explicit. No background monitoring, automatic tagging/assignment, saved findings review workflow or customer messaging actions are implemented yet.

Full suite: 35 tests passed. Regression coverage includes actual conversation context with no outbound message or queue write, source persistence, enable/disable, deletion, limits, permissions and workspace isolation. Model responses in tests are controlled doubles. Real AI generation, live Meta operation and current UI visual verification remain pending.

## Adopted feature update — 29 October 2026

This update implements working parts of the requested WATI/competitor feature set. Full WATI parity and production readiness remain incomplete.

- **Sales pipeline:** persistent contact-linked opportunities, New/Qualified/Proposal/Won/Lost stages, team owner, validated integer minor-unit amounts and separate currency totals. Values are team-entered estimates, not payment receipts or attributed revenue. Deal contact changes are blocked while linked follow-up tasks exist.
- **Follow-up tasks:** contact/deal links, owner, optional timezone-aware due date, overdue display, complete/reopen and editing. Tasks do not trigger automatic WhatsApp messages or notifications.
- **AI findings:** saved-agent on-demand analysis, persistent run history and pending findings with supplied message references. The local model receives the existing bounded workspace context and must return strict structured JSON. Unsupported actions, invented references and malformed output cause an explicit failed run; no canned findings are supplied.
- **Human review:** admins may dismiss, acknowledge, or apply one allowed local proposal: add tag, assign to a human, add internal note, create reply draft or create follow-up task. No sending, payment, arbitrary HTTP/API request, blocking or deletion action is available. Each finding is applied at most once inside a transaction and audited.
- **Stale protection:** model context and proposal fingerprints derive from one database read snapshot. Changed contacts/messages or findings older than 24 hours cannot be applied. Applying a proposal to a contact invalidates other findings for that same contact; run a fresh analysis for further changes.
- **Human takeover:** the inbox offers Take over / Resume automation. Takeover assigns the chat to the operator and pauses keyword/graph processing. Graph handoff and approved agent assignment also hold the conversation. Incoming messages and STOP consent processing continue. Resume explicitly resets any previous flow session. Campaigns are managed separately.

Verification: **50 Python tests passed**, including HTTP persistence/assets and both independent-review regressions. Python compilation, all JavaScript syntax checks and Node UI renderer smoke checks passed. The latter cover pipeline/findings rendering, escaping, role visibility and inbox takeover controls, not real-browser visual appearance. Independent code review found a stale-context race and linked-task contact inconsistency; both were fixed and rechecked with no remaining findings within that review scope.

REA re-observation: `ev_fe6458037ca09f1682210a0bc5fc3348a75c3b9a5c32402156697ead8505fd10` confirms the observed eleven-agent catalog. No WATI Hire, Send, activation or settings changes were made. No paid APIs or real provider calls were used in verification. Real Ollama answer quality, Meta delivery and latest visual parity remain unverified.

Still pending: scheduled/background agents, richer findings/actions, customer-facing AI execution, broader workflow triggers, round-robin/availability routing, commerce/store/payment adapters, omnichannel support, production onboarding/billing/hosting and the rest of PARITY.md. This update does not make the entire WATI clone complete.

## Current AI increment — 29 October 2026

Background schedules, pause/resume, agent edit/archive/restore, activity history, private agent-bound chats, selected-conversation context and the OpenAI Responses adapter are implemented. All eleven observed role presets plus Daily Digest are present. Keys stay server-side; OpenAI paid calls require a separate per-workspace approval flag. No paid calls were performed.

**66 Python tests passed**, plus Python compilation, all JavaScript syntax checks and UI renderer/chat-race checks. Current visual parity, exact WATI agent forms/mode choices/review behavior, private backend equivalence and real OpenAI/Meta execution remain unverified. Exact WATI parity is not complete. See [AI release scope](docs/background-ai-release.md) and [acceptance ledger](docs/wati-ai-parity-checklist.json).


Scheduler tests cover restart persistence, missed interval skipping, pause/archive, manual overlap, lease loss, archival restoration and per-workspace OpenAI opt-in. Provider tests use controlled transport responses, including refusal, incomplete/malformed output and sanitized errors. Independent review fixes are documented in docs/background-ai-release.md. No paid provider inference, actual message delivery or latest visual QA was performed.
