# One-time team invitations

Workspace administrators can create an agent or administrator invitation for a specific email with a 1–168-hour lifetime. The link is returned once for manual private sharing. No email is sent. The local server remains bound to loopback; recipients on other computers cannot use the link until the application is separately hosted.

Only a SHA-256 hash of the random 256-bit token is stored. Invitation listings expose status, recipient, role and expiry, never tokens or hashes. A workspace permits up to fifty pending invitations and one active invitation per email. Administrators can revoke unredeemed invitations. The issuer must still be a workspace administrator when an invitation is inspected or redeemed.

The browser receives the token in a URL fragment and removes that fragment before issuing inspection requests. The token is retained only in the invitation UI's memory. Public inspect/accept requests use POST bodies, same-origin checks and the authentication endpoint's local rate limit. Request logging is disabled. The token is not written to localStorage or ordinary application state.

New recipients choose their name and password. Existing accounts must verify their current password; an invitation cannot reset that password, rename the account or promote someone already in the workspace. Acceptance, membership creation, token consumption and session issuance occur in one transaction. Competing redemptions create at most one membership. Invalid passwords leave the invitation unconsumed.

This is team invitation onboarding, not complete production client onboarding. Email delivery, public signup, billing/plans, SSO, recovery, granular roles, public HTTPS hosting and full production security/operations remain pending. Domain and HTTP tests use temporary local databases; no invitations or messages were sent externally.
