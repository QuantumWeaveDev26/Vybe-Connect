# Account MFA release increment

Implement optional account-wide authenticator MFA without activating it on existing accounts. Use RFC 6238 SHA-1, six digits, 30-second steps, a one-step clock tolerance and transactional replay protection. Add ten single-use recovery codes stored only as hashes. Protect enrollment, disable and recovery-code rotation with current-password verification and existing session validation; enabling and disabling revoke all sessions. Existing-account invitations must enforce the same second factor as login. Password recovery must preserve MFA.

1. Write failing algorithm, lifecycle, invitation and concurrency tests using temporary databases.
2. Add a focused `account_mfa.py` module and an additive table. Wire login, invitations, account HTTP endpoints and authenticated status without exposing secrets in workspace state.
3. Add account-security controls, manual authenticator provisioning, recovery-code display, and optional second-factor fields on login/invitations. Keep codes out of browser storage. Clear enrollment secrets after closing the dialog.
4. Run focused tests, full regressions, renderer/syntax checks and local HTTP acceptance. Update the production audit and source archive. Actual device/provider and deployed security review remain separate gates.
