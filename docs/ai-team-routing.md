# AI handoff team pools

Customer support AI setup now offers fixed routing or least-busy routing across a selected pool of up to 50 current workspace members. Existing installations retain fixed routing by default. No model, Meta connection or paid calls are needed to configure routing.

An active conversation assignee is always preserved, including an assignee outside the configured pool. Otherwise, least-busy routing counts each eligible member's assigned Open and Pending conversations in the current workspace, excluding the conversation being handed off. Solved conversations do not count. The configured pool order breaks ties. The UI stores members in displayed team order; API callers can provide an explicit order.

Removed members are ignored at runtime. If no selected member remains, the current assistant administrator is used if still a member; otherwise the handoff remains unassigned. The routing reason, eligible-member count and chosen member's load before assignment are recorded as a snapshot in handoff details. They are not live workload figures.

The existing write transaction covers selection, assignment and optional internal task creation. Concurrent handoffs see earlier committed assignments rather than all selecting from the same old snapshot. Settings edits retain the existing job-version fence and suppress pending/generated replies from an older policy. This applies to model-requested handoffs, provider failures and interrupted jobs through the existing shared handoff function.

Membership does not indicate online availability. There is no presence tracking, business-hours policy, capacity threshold, SLA escalation or external notification in this increment. No customer message is sent by routing. An AI finding approved as a human assignment now also removes pending flow/wait and no-response continuations, keeping later resume from reviving old automated work.

REA's WATI captures remain inspection evidence only; these routing semantics are independently implemented and are not proof of WATI backend equivalence.
