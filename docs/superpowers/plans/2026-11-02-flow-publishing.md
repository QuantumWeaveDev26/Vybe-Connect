# Chatbot draft and publish increment

Keep existing active flow execution and delivery fences. Add independent saved drafts, optimistic draft/base-version checks and immutable version snapshots. Draft saves do not change the active keyword, graph, delivery mode or running sessions. Explicit publication validates graph/member/resources, records a version and cancels old sessions using the existing fences. Legacy `flow.save` remains an explicit publish operation and also records immutable snapshots. New UI flows start disabled until publication. Restore copies historical configuration into a draft; it never activates a version directly.

Implement in a focused module plus additive table, admin-only action dispatch, scoped state projections and graph editor controls. Verify draft isolation, publication, history immutability, concurrent editors, stale drafts, tenant/role boundaries and restore semantics. Preserve existing delivery/provider gates and run the full regression suite.
