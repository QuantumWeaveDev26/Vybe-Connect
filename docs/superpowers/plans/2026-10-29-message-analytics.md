# Recorded message analytics implementation plan

Continue inline with TDD. Authenticated workspace report over the complete messages table, independent of the inbox's 2,000-message window. Inclusive UTC date range, at most 366 days; zero-fill daily buckets. Count received inbound and actual outbound states (accepted/sent/delivered/read/failed/unknown), excluding drafts, simulations and internal notes. Provider acceptance, recorded delivery and read remain distinct; uncertain submissions do not count as delivery.

Return aggregate traffic, distinct contacts and daily state counts without contact text/identifiers. UI date controls, accessible chart/table and local CSV export use only the current scoped report. Guard late responses after workspace/user/range changes. Current workload stays explicitly a present-time snapshot. No synthetic response-time, revenue or customer-satisfaction metrics.

- [x] Add failing date/range, status, history-size, tenant and aggregation tests.
- [x] Implement indexed SQL aggregation and authenticated HTTP report endpoint.
- [x] Add scoped date controls, daily chart/table and CSV export.
- [x] Run domain/HTTP/renderer checks, document limitations, package and restart.
