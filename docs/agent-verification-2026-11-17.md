# Agent reliability follow-up — 17 November 2026

No paid provider calls, Meta sends, payment requests or new services were activated in this follow-up. These checks use isolated synthetic databases and simulated HTTP responses; they do not establish live model quality for every preset.

## Fixed

- Conversation evidence now excludes unsent drafts, failed/uncertain outbound text, simulated inbound messages and private notes. Delivery-error counts remain available separately.
- Scheduled agents retain their due run while a known provider cooldown is active or the included subscription request allowance is empty. They can resume when access returns without producing repeated failed runs or new paid submissions during the pause.
- Agent analysis excerpts long reference bodies and reduces optional samples within a 22,000-byte facts budget before reserving subscription usage. Evidence objects remain intact, newest conversation samples are preferred, and saved run history records the reduced sample size and partial scope. Excessively large mandatory instructions still fail before spending.
- Current membership is checked before agent execution and before publishing findings. Scheduled runs also require their owner to remain an administrator.
- Queued chat answers and agent-builder proposals are discarded if their owner loses the required access during generation. Provider refusals, incomplete output, malformed findings and transport failures publish no dummy answer and are not automatically resubmitted.

## Preset coverage

`tests/test_agent_acceptance.py` exercises both saved-agent findings and queued, cited chat answers through the actual OpenAI adapters, replacing only HTTP transport, for all twelve visible presets:

Daily Digest; Inbox Triage; Re-engagement Scout; Urgency Watcher; Top Topics; Spam Watcher; Ready-to-Buy; Automation Health Check; Campaign Readiness Checker; Segment & Contact Checker; Campaign Idea Finder; Account Health Checker.

The matrix verifies the configured model, original instructions, structured schemas, review-first persistence, queued reply completion and absence of outbound delivery. Additional regression cases cover pause/recovery, an exhausted allowance, large subscribed workspaces, stale/removed membership and provider failures. Customer support, subscription entitlement, scheduling, cancellation, source validation and the full application suite are checked separately.

## Remaining acceptance

The earlier explicitly approved live smoke test covered Daily Digest and a grounded customer-reply draft. This follow-up spends nothing further. Live acceptance of every preset, real customer checkout, Meta onboarding/calling, mailbox delivery and physical devices remain separate checks. Meta review and real billing credentials cannot be replaced with simulated approvals, subscriptions or test responses.
