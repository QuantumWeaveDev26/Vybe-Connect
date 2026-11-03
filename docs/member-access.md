# Workspace member access

The team screen lets administrators change admin/agent roles or remove workspace access. The server rechecks the acting administrator inside the write transaction. It prevents removal or demotion of the final administrator, including simultaneous self-demotions. Agent and stale administrator contexts cannot change membership.

Removal deletes only that workspace membership. Global identity, passwords, other memberships and conversation history remain. Contact assignments and open task ownership become unassigned; completed tasks retain their historical owner identifier. Losing administrator status revokes that member's pending invitations in the workspace. Future authenticated requests use the current membership and role.

When a workspace state request returns forbidden, the browser clears cached workspace data before trying another accessible workspace or returning to sign-in. Already authorized in-flight requests and provider submissions cannot be recalled by removal. This does not provide global account deactivation, SSO, granular permissions, recovery or complete production authorization hardening.

Local tests verify scope, role changes, last-administrator concurrency, issuer revocation, assignment cleanup, next-request access denial and browser cache clearing. No external notification or provider call is made.
