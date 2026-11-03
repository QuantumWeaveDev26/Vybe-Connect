# Team operations and routing

Add workspace-scoped named teams with optimistic versions, admin membership management and archival. Add self-managed availability (available for 15–480 minutes, away or offline); this is an explicit routing signal, not browser online presence. Preserve existing routing by default. Let customer AI optionally use a current team, require available members and enforce an open/pending workload cap. Preserve existing assignees; when the stricter configured policy has no eligible member, leave the handoff unassigned rather than bypassing the policy.

Add explicit team routing for unassigned conversations and a bounded assignment timeline. Route under a write transaction using current membership/team/availability/workload; retain existing round-robin persistence and concurrent least-busy guarantees. Remove departed members from teams and availability. Team membership does not introduce new conversation-visibility permissions.

1. Write failing lifecycle/routing/isolation/concurrency tests in temporary stores.
2. Implement team_operations.py; integrate state/actions, existing handoff selection and member cleanup.
3. Add team management, personal availability, routing controls and assignment history to the UI. Escape all user text and fence asynchronous workspace changes.
4. Verify HTTP and renderer behavior, run regression/syntax checks, update audit and archive. No real account/provider activation or paid calls.


Collaboration extension: keep private notes in the existing internal-message path. Record authors and explicitly selected current-member mentions; create one in-app notification per mentioned recipient. Only the recipient can mark their notification read. Notes remain excluded from customer AI context and never enter provider queues. Add author rendering, a comment/mention form and recipient notification navigation, with tenant/member/flag validation and HTTP/privacy regression checks. Comment editing/deletion, email/push delivery and historical authorship reconstruction are outside this increment.
