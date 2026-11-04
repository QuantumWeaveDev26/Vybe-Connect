# Public business registration and remembered sign-in

The user explicitly clarified that VYBE Connect is a public business platform. Initial-owner setup alone is insufficient. Implement a separate public Create account flow: each new email/password account receives its own isolated business workspace. Existing accounts sign in normally; arbitrary unknown credentials must not be accepted as a login. Initial platform-owner setup remains protected and public signup cannot claim an uninitialized deployment.

Keep me signed in uses a 30-day Secure/HttpOnly/SameSite session cookie backed by the same server-side expiry. Unchecked retains the existing 12-hour session. Logout and password/security revocation invalidate remembered sessions. Never store passwords in browser storage. Browser password-manager autofill remains available.

- [x] Write failing store and HTTPS HTTP tests for explicit signup gating, owner protection, validation, duplicates, isolation, platform-operator separation, rate/origin checks and persistent session/logout behavior.
- [x] Implement transactional public signup and bounded session durations; advertise signup availability in bootstrap and add the guarded endpoint.
- [x] Add concise Create account / Sign in navigation and Keep me signed in controls, preserving password visibility and MFA. Public signup creates accounts, not verified email identities. Email delivery remains unavailable and no email-verification claim is made.
- [x] Run auth/MFA/invitation/HTTP and full regression checks, UI tests and code review. Deploy with TW_PUBLIC_SIGNUP=true as explicitly requested; preserve scoped provider settings and activation gates.
- [x] Inspect the live public forms without creating a synthetic production account. Verify registration persistence and isolation in isolated test databases. Finish the live mobile/AI/password-control checks from the preceding pass.
