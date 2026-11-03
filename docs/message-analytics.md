# Recorded message analytics

The Analytics screen queries the complete workspace message table rather than the inbox's latest 2,000-message window. Select inclusive UTC dates spanning at most 366 days. Daily buckets are zero-filled and available as a local CSV download. Current operator workload is explicitly a present-time snapshot, independent of the selected period.

Traffic includes recorded received inbound and outbound accepted, sent, delivered, read, failed, unknown and sending states. It excludes drafts, simulations and private notes. Counts group by message creation/submission timestamp and show each message's latest recorded status, not the date when a later delivery webhook arrived. Consequently later webhooks can change a past day's status distribution.

Accepted-or-later counts combine accepted/sent/delivered/read. Recorded delivery combines delivered/read; read remains separately visible. Failed, unknown and in-flight submissions do not establish delivery. Distinct contacts count only records included in this report. Aggregate responses contain no message text or contact identifiers. Counts represent local records and are not independently reconciled with a provider export.

The authenticated endpoint is /api/analytics?from=YYYY-MM-DD&to=YYYY-MM-DD. The SQL scope checks current membership and uses the tenant/time index. Frontend reports and exports are scoped to workspace and user, and delayed responses cannot populate a different workspace. Sign-in/access-loss flows clear report state.

Historical response/resolution times, sales attribution, calling, chatbot performance, CX/topic analytics, custom dashboards and scheduled report delivery remain incomplete. No AI request or external provider operation is used to generate this report. Automated checks cover UTC bounds, leap years, missing days, traffic states, records beyond the inbox window, membership/tenant scope, HTTP access and stale-response protection.
