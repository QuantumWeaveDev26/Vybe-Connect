# Services and AI acceptance — 6 November 2026

## Verified

* Full regression suite: 672 tests, 671 passed and one platform-specific skip. After the services fixes, 36 targeted services/billing/deployment checks passed, including three new resource-identity/status/period tests.
* All 28 JavaScript suites passed. Added a delayed-response/workspace-switch test proving service results cannot close dialogs or refresh another workspace.
* Live authenticated browser inspection: services connections, subscription setup, AI agent catalog and Daily Digest activity rendered. Daily Digest had no recorded production runs; no production agent run was triggered.
* One real OpenAI acceptance request used the app's actual `ai.run` path in a temporary isolated Store, a synthetic customer inquiry and the existing private OpenAI key. Model: gpt-6-luna; max output 512 tokens; no tools, retries, Meta calls, production customer data or persistent production records. Result completed, parsed and recorded one grounded informational finding. Input 1,171 tokens; output 91; total 1,262; recorded cache-write tokens 1,168. Conservative published-rate estimate below US$0.001, not an invoice reconciliation. Original instructions correctly avoided inventing business opening hours.

## Fixed

* Payment reconciliation and signed payment/subscription updates now enforce the previously recorded provider resource ID, recognized statuses and valid subscription-period types before updating access/payment state.
* Service actions recheck the workspace and user after provider responses, preventing stale results from affecting a newly selected workspace's dialog.
* Connections distinguish Setup needed from Activation needed instead of showing every unavailable provider simply as Disabled.

## Configuration and remaining acceptance

Live Razorpay billing KEY_ID, KEY_SECRET, WEBHOOK_SECRET, ACCOUNT_ID and subscription plans are absent. Billing activation, live approval and subscription enforcement are off. No payment, refund, subscription authorization, shipping operation or Meta request was tested live. These cannot honestly be declared working end to end without configuration and provider acceptance. No paid client access or prices were invented.

All twelve agent presets share locally tested execution/permission contracts; the real model acceptance above covers one synthetic agent, not every preset or all customer scenarios. Live delivery/calling, commerce, Google and recurring-payment acceptance remain separate.

## Repository downloads

Sources downloaded for read-only review under `C:/Users/pavan/OneDrive/Documents/ChatGPT/VBYE CONNECT/research`:

* evolution-api: fa09d37892cdbb1d65a250155d293d92230c5b30
* new-api: e03439033238722c0b8d4437a052445f3aeeed83
* Routerly: d605c0a81a814264ecf64cd5011030d17c065f6b

No repository runtime was installed or executed, no new transport activated, and no licensed gateway source silently merged. The existing original gateway adapter remains available when an operator configures a compatible endpoint.
