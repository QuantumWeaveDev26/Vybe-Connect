# Competitor features and deployment scope — 2 November 2026

The user added respond.io team operations, SleekFlow business knowledge and Interakt sales CRM to the full WATI-equivalent goal. “Intcrakt” is interpreted as Interakt because its official sales-pipeline product matches the request. Research used public official documentation; no authenticated walkthrough or account connection was performed.

## respond.io: team operations

Official sources: [team collaboration](https://respond.io/help/inbox/collaborating-with-your-team-in-inbox), [inbox overview](https://respond.io/help/inbox/getting-started-with-inbox), [workflow overview](https://respond.io/help/workflows/workflows-overview).

Relevant ideas: team inboxes, collaborators/internal comments, assignment history, least-open and round-robin routing, availability-aware routing and business-hours handling. The current build already has assignment, notes, takeover and least-busy AI handoff pools. Round-robin AI handoff pool rotation is now implemented and persists across restarts. Managed teams, expiring personal availability, capacity/availability routing policies, explicit team routing, assignment history and private note mentions with recipient notifications are now implemented locally. Still to implement: collaborator visibility, browser presence, business hours, automatic backlog redistribution and fuller operations reports. Product UI access and complete parity are unverified.

## SleekFlow: business knowledge

Official sources: [knowledge source management](https://help.sleekflow.io/agentflow/add-sources-to-your-sleekflow-ai-knowledge-base), [source assignment](https://help.sleekflow.io/en_US/assign-and-manage-sources-in-your-sleekflow-ai-knowledge-base), [agent analytics](https://help.sleekflow.io/en_US/agentflow/ai-agent-analytics).

Relevant ideas: shared source library with agent-specific selection, source processing status, testing/citations and source-usage analytics. The build already has files/manual sources/public-page ingestion, explicit support-assistant source approval and validated citations. Thirty-day recorded document-reference usage and customer-AI outcome counts are now implemented. Still to implement: a reviewable unanswered-question queue, broader agent-specific knowledge policies and fuller source-readiness reporting. Do not invent grounded answers or silently call paid providers to fill gaps.

## Interakt: sales pipeline

Official source: [sales pipeline guide](https://www.interakt.shop/resource-center/managing-sales-pipeline/).

Relevant ideas: configurable stages, visual lead movement, owner/task/chat shortcuts, closure deadlines and visibility into stage progress. The current build has a fixed five-stage deal board, amounts/currencies, contact links and follow-up tasks. Workspace-configurable stages, closure due dates, stage-change timeline and overdue views are now implemented. Advanced pipeline automation, document management and external deadline notifications remain incomplete. Revenue remains a staff-entered estimate, not a payment or campaign-attribution claim.

## Release requirements

Prepare one-instance deployment behind an HTTPS reverse proxy with exact public-origin/Host checks, secure cookies, protected initial owner setup, health/readiness endpoints, persistent private data and documented backup/restore. Container and external HTTPS behavior require actual verification; source configuration alone is insufficient. Do not publish to an unsolicited hosting service or enable live Meta/OpenAI usage. Account recovery, advanced access policies, full integration parity and live-provider acceptance remain release gaps to track explicitly.

This document extends the original goal; it does not replace it with only these features or assert deployment readiness.
