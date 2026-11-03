# One-time team invitations implementation plan

Continue inline with TDD. Administrators create/revoke workspace invitations with a role, email and 1–168-hour lifetime. Store only a SHA-256 token hash; return the random token once. List projections exclude hashes/tokens. Limit pending invitations. Issuer must remain an administrator at redemption. New recipients choose their own password; existing accounts must verify their current password without any reset. Acceptance, membership creation, token consumption and session issuance are atomic.

Add rate-limited same-origin public inspect/accept endpoints. Browser links carry the token in the fragment, remove it from the address bar immediately and retain it in memory only. The invite UI never adds it to localStorage or ordinary app state. Administrators copy links manually; no email is sent. The app remains loopback-only until separately deployed. Public client self-signup, billing, SSO and recovery remain pending.

- [x] Add failing token, scope, expiry, issuer-role, replay, existing-identity and credential tests.
- [x] Implement hashed invitations, atomic acceptance and authenticated projections/actions.
- [x] Add invite management and recipient acceptance UI with URL cleanup and scope checks.
- [x] Run provider-free domain/HTTP/renderer regression, update coverage and source package, restart locally.
