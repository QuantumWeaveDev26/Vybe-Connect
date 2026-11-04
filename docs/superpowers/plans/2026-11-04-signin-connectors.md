# Sign-in and connector navigation improvements

The user requested easier sign-in and supplied screenshots of the existing sign-in/recovery screens and WATI connector/developer navigation. Continue in the existing checkout and green theme. Preserve authentication, MFA, existing sessions, provider gates and real data. No password reset, paid provider call or new public API permission is implied.

- [ ] Add a focused sign-in presentation module: browser autofill, show/hide password, Caps Lock notice, initially collapsed MFA controls with automatic expansion on a server MFA rejection, busy states, clear errors, and stale-form response guards. Keep the existing login endpoint and password policy.
- [ ] Add a keyboard/click/hover connector popover linking to actual API contract, integrations and webhook delivery screens. Provide a real webhook screen and a setup checklist reflecting current connection state; do not present an unsupported API-key generator.
- [ ] Prepare private Gmail SMTP configuration. Configure and test authentication only if the owner supplies an App Password privately. Do not pretend email recovery works without it, and do not send mail without explicit recipient/test authorization.
- [ ] Run isolated UI lifecycle tests, all-route rendering, auth/MFA/recovery and full regression checks. Browser visual/device QA remains blocked by Work settings.
- [ ] Review, publish, pin the verified release, and deploy while preserving the private Compose token override and latest environment. Verify live assets, health, auth boundaries and webhook afterward.
