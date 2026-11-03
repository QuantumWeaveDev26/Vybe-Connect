# Workspace member access implementation plan

Continue inline with TDD. Administrators can change admin/agent roles or remove workspace access. Check actual administrator membership inside the write transaction and preserve at least one administrator, including concurrent changes. Removing access affects only that workspace, clears its open contact/task assignments, and retains global identity, other memberships and conversation history. Losing administrator status revokes outstanding invitations issued by that member.

Add reviewed UI controls and clear cached private workspace state after a forbidden state response before selecting another accessible workspace or showing login. Existing in-flight provider operations and independently authorized requests cannot be recalled. No email or external notifications.

- [x] Add scope, last-admin, concurrency, assignment and invitation revocation tests.
- [x] Implement transactional member actions and removal cleanup.
- [x] Add team controls and stale-access UI clearing.
- [x] Run local domain/HTTP/renderer regression, update boundaries/package and restart.
