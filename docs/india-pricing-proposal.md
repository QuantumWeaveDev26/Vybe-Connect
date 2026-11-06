# Proposed India launch pricing

Decision date: 6 November 2026. Commercial proposal only: these are not active Razorpay subscriptions or enforced product entitlements yet.

| Plan | Monthly platform fee | Proposed included AI cost allowance |
|---|---:|---:|
| Starter | INR 499 | INR 25 |
| Growth | INR 999 | INR 75 |
| Scale | INR 1,499 | INR 150 |

Applicable taxes are separate. Official WhatsApp/other external provider usage is separate and must be disclosed before purchase. Do not describe unofficial QR transport as an equivalent official Meta service. No unlimited AI, unlimited support or unverified feature promises.

Emovur's public pricing page currently lists Starter at INR 999/month-equivalent and Advanced at INR 1,999/month-equivalent, with an annual/quarterly billing selector. Our Starter proposal has a lower listed entry price; term-specific comparisons must use the actual billing contract. Source: https://emovur.com/whatsapp-business-api/pricing . Emovur also has a free tier, so we cannot claim to be cheaper than every Emovur plan.

## Profitability guardrails

These are planning assumptions, not measured margins. For each plan, keep combined non-AI delivery costs (payment processing, hosting allocation, support, storage and monitoring) below INR 200 / 400 / 600 respectively. With fully consumed proposed AI allowances, contribution before taxes, acquisition costs and other overhead would be INR 274 / 524 / 749. Validate these budgets using actual invoices and support effort before launch; profit is not guaranteed.

AI allowance means a rupee-denominated provider cost budget, not a number of messages. Currency conversion and model prices must be recorded. The present daily gateway request cap is not this monetary allowance. Before publishing these entitlements, implement atomic monetary reservations, reconciliation, exhausted-budget behavior, subscription entitlements and separately authorized top-ups. Do not silently charge for overages.

## Activation work

1. Configure the platform Razorpay merchant credentials and signed webhooks privately.
2. Create verified monthly INR plans for 49900, 99900 and 149900 minor units; save their real plan IDs in TW_BILLING_PLANS. No dummy plan IDs were created.
3. Implement and test the proposed monetary AI allowances before displaying them as included entitlements.
4. Complete real subscription authorization/renewal/cancellation acceptance, backups and support arrangements before turning on paid-client enforcement.

No merchant account, subscription, checkout or billing enforcement was activated by this proposal.
