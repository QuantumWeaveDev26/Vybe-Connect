# Workflow and live AI acceptance - 6 November 2026

## Real OpenAI checks

Used the existing platform key, verified privately against the deployed configuration, with only synthetic temporary Store data. All twelve shipped preset instructions were loaded from the UI catalog and run through the real ai.run path. Additional real checks exercised durable queued Ask, AI agent-builder proposal generation and the customer-assistant worker creating a grounded unsent reply. Fifteen model submissions, fifteen successful scenarios, zero automatic retries and no Meta requests. All queued chat jobs completed; no uncertain provider reservations remain.

The acceptance harness lowered output limits to 1,024 tokens, allowed only gpt-6-luna and OpenAI Responses egress, persisted a preflight budget reservation before every paid submission and retained reservations for uncertain outcomes. User cap: US$0.40. Conservative usage-based upper estimate: US$0.039462, using deliberately high rates of US$1/M input and US$5/M output. This is not invoice reconciliation. Official model pricing reference: https://developers.openai.com/api/docs/models/gpt-6-luna . No additional chargeable tests were performed after this run.

| Scenario | Result |
|---|---|
| Preset: Daily Digest | Passed |
| Preset: Inbox Triage | Passed |
| Preset: Re-engagement Scout | Passed |
| Preset: Urgency Watcher | Passed |
| Preset: Top Topics | Passed |
| Preset: Spam Watcher | Passed |
| Preset: Ready-to-Buy | Passed |
| Preset: Automation Health Check | Passed |
| Preset: Campaign Readiness Checker | Passed |
| Preset: Segment & Contact Checker | Passed |
| Preset: Campaign Idea Finder | Passed |
| Preset: Account Health Checker | Passed |
| Queued AI Ask with grounded citations | Passed |
| AI agent builder proposal | Passed |
| Customer support grounded reply draft | Passed |

## Authenticated live browser workflows

Created an isolated, clearly labeled QA Acceptance - No Sending workspace under the existing owner. Created and edited one text template with header, body, name variable, footer and a quick-reply button. Saved one campaign draft with an explicit QA tag, and switched its list/calendar views. Created one synthetic non-consenting contact at a reserved fictional phone number, with custom attributes. Saved one private inbox note, changed the conversation to pending and verified its Pending filter. Created one on-demand Daily Digest agent and one disabled keyword rule whose only configured actions are tagging and an unsent draft. No schedules, subscriptions, live messages or provider approvals were activated. These records remain isolated for owner inspection; no production data was replaced or fake subscription state inserted.

Navigated all 31 named app destinations in this QA workspace: every route rendered its expected page heading without page-wide horizontal overflow at the current phone viewport. This is a navigation smoke check, not proof that every possible button, integration or customer scenario works. AI in the unsubscribed QA workspace correctly showed subscription-required guidance; the fifteen real model checks above used a separate temporary test Store with explicit paid-call authorization and the same actual platform key.

## Fixed from this pass

* Disable template submission when WhatsApp configuration is unavailable and campaign launch until sending and a synced approved template are available. Server validation remains authoritative.
* Lock template saves while pending, preserve new-workspace drafts from old save responses, and prevent stale action-button dialogs from editing another workspace's template.
* Give shared checkbox fields real accessible labels and clickable label text.
* Replace obsolete team-page setup claims with current role/recovery guidance; use actual campaign status in calendar entries.

## Regression and limits

Full Python discovery: 682 tests, one skipped, all others passed. Three additional budget-guard checks passed. All 30 JavaScript suites passed; focused template/startup/renderer checks passed after the final template-dialog guard. The UI detector reported no findings in the changed JS targets; this does not certify WCAG compliance.

Razorpay keys/real plan IDs remain absent, so real checkout, authorization, renewal/cancellation and refunds were not tested. No shipping or WhatsApp message/call was sent. Official Meta customer onboarding/approvals and live delivery/call acceptance remain separate. Google OAuth and other unconfigured external endpoints were not represented as live successes. These checks do not establish full WATI parity or comprehensive paid-client readiness.

## Verified deployment

Hostinger VPS 1871828, project vybe-connect, action 124094890 succeeded. Runtime source e5aaaa516697222272e5a6c34fbc82239266422c. App healthy; source initializer exited 0. Deployed Compose matched the candidate and private environment was unchanged. Live index and all 45 referenced JS/CSS assets matched the pinned Git source byte for byte. Six public health/authentication/private-path checks passed, including that the acceptance harness is not publicly served.

Authenticated post-deployment browser checks confirmed Submit to Meta and Launch campaign are disabled in the unconnected QA workspace; the existing template/footer persisted across restart, and the new save lock disabled the editor while its request was pending. Contact marketing consent now exposes its complete accessible label. The QA campaign remained a draft with zero audience, zero queued messages and no send event. No extra paid model requests were made during rollout.

Final browser pass: saved template edit rechecked after deployment; rendered at requested 390 and 1280 pixel widths without page-wide horizontal overflow. The current owner workspace selector was restored to QuantumWeave AI; the clearly labeled QA workspace remains available separately. No browser errors were captured in the final pass.
