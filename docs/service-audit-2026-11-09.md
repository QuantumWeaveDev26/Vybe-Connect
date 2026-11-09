# Service audit — 9 November 2026

## Current evidence

Live health, readiness and bootstrap returned 200. Anonymous workspace state returned 401. In the existing isolated QA Acceptance — No Sending workspace, the template footer edit persisted, a new unscheduled campaign draft saved with zero audience and zero outbound jobs, and a private inbox note persisted. No WhatsApp messages, template submissions, calls, shipments or payments were made.

All 31 main routes rendered at 390×844 and 1280×900 without page-wide horizontal overflow or a page-level internal-error message. All twelve preset setup forms opened with the expected agent names. Browser error capture was empty. These are workflow and navigation checks, not exhaustive button, device or provider certification.

Baseline Python discovery passed 700 tests, one skipped. After repairs, discovery passed 708 tests, one skipped. All 31 JavaScript suites passed. The four acceptance-budget guard checks passed separately. The twelve built-in preset runs passed local rules-engine execution/validation; this does not establish language-model quality.

## Repairs

- Website chats now use random, expiring visitor credentials stored as hashes. History requires the visitor credential and matching contact. Submitted phone numbers cannot impersonate or merge into a WhatsApp customer. Website chats create distinct non-consenting contacts and support actual first-party inbox replies without a Meta request. Public traffic is bounded per tenant/session. Old insecure widget sessions must start a fresh conversation.
- API sending now requires a separately selected messages:write scope. Existing read tokens retain read-only access. Sending uses the real inbox adapter with its service-window, live-provider and subscription checks. Missing contacts and unsupported interactive button payloads fail explicitly; no automatic contact consent or simulated success is created.
- Production simulator actions are rejected on the server and their buttons are hidden. The unsupported quick-button composer control was removed. Solving a production conversation no longer inserts a pretend CSAT delivery.
- Managed AI does not fall back to a local engine when platform configuration is missing. Local rules are labeled as rules with no language model. A failed Ollama request cannot produce a canned fallback, and rules cannot manufacture a high-confidence customer answer or pretend to generate an agent.
- The optional paid acceptance harness stops subsequent provider requests after a provider/transport failure.

## Live AI and remaining acceptance

The new synthetic-only OpenAI acceptance attempt was capped at US$0.10 (below the previously authorized US$0.40 total ceiling). HTTP 429 rejections occurred; no completed response/token usage was verified. Testing was stopped. The durable ledger conservatively retains US$0.097707 for eight submitted/unconfirmed requests, with zero confirmed token cost. This is an upper reservation, not an invoice. Do not call these live AI tests passed or claim zero charges. No further paid requests are authorized by this report.

The live QA tenant has AI runs paused. Platform OpenAI quota/model/billing and paid-tenant eligibility need successful acceptance before live agents can be called operational. Real Meta delivery/calling, customer Embedded Signup approval, Razorpay subscription lifecycle, Shiprocket operations, recovery-email delivery and complete device testing remain separate gates. UI checks and mocked provider contracts do not close those gates.

Deployment evidence will be added only after the running release and public assets are verified. Production data and private environment values must be preserved.
