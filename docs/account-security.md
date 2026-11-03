# Account security: passwords, authenticator MFA and recovery

Signed-in users can choose **Password** in the sidebar. The form verifies the current password, checks a new 12–256-character password and confirms it locally. A successful change replaces the salt/hash and revokes every session for that account across all workspaces, including the current browser. Sign in again afterwards. Other accounts, roles, workspace memberships and business records remain unchanged.

The HTTP endpoint requires an authenticated session, the exact same Origin and the existing bounded authentication-rate controls. It accepts no target account identifier; the authenticated account is always the target. Passwords are sent in the POST body, never a URL. Production mode requires the configured HTTPS origin. Secrets are not added to audit events or browser storage. The browser clears private workspace/AI state after a successful change.

Password verification, replacement and session revocation use a write transaction. Login also rechecks the stored hash/salt before creating a session, so an old-password login racing a reset cannot recreate access afterwards. Requests already authorized and sent to external providers cannot be recalled, and scheduled automation configuration is not changed by a password operation.

## Forgotten password: server operator only

Self-service email reset is implemented behind a disabled SMTP gate; see email-recovery.md for configuration and live-delivery limitations. Authenticator MFA is optional and is described below. Password recovery does not disable MFA. Until those are added and verified, forgotten-password recovery requires an operator with legitimate access to this application's server and private database. This tool is not an API and does not access WATI or any other service account.

Stop the application, preserve a backup and open an interactive terminal on the server. For the packaged Docker topology, use the actual active data path and target account email:

```sh
docker compose --env-file /private/teamwave.env stop app
docker compose --env-file /private/teamwave.env run --rm --no-deps -it app python recover_account.py --db /var/lib/teamwave/active/teamwave.db --email owner@example.com --offline-confirmed
docker compose --env-file /private/teamwave.env up -d app
```

The new password is entered twice using a hidden terminal prompt. Non-interactive input, password command-line arguments and password environment variables are not supported. The existing database/account must be found first; the tool will not create one for a misspelled path or email. It revokes all sessions and records a security audit event, but grants no role or workspace access. Test the restored login and preserve the operator audit trail.

No actual owner password was changed during development. Tests used temporary accounts/databases. Local automated checks do not establish container interaction, operational recovery procedures, device-level MFA acceptance or complete production readiness.


## Authenticator MFA

Choose **Security** in the sidebar. Enter your current password to generate a private setup key, then add a time-based account in your authenticator app. Use SHA-1, six digits and a 30-second interval. Manual entry is supported; QR rendering is not included. Setup expires after ten minutes. MFA becomes active only after you enter a valid code and your current password. Enabling it revokes all sessions across all workspaces. Save the ten single-use recovery codes shown once, then sign in with your password and a fresh authenticator code.

The implementation follows [RFC 6238](https://www.rfc-editor.org/rfc/rfc6238). Verification permits the previous/current/next 30-second step for clock tolerance and transactionally rejects every previously accepted counter. A code used to confirm enrollment cannot be reused for login. Wait for a fresh code or use a recovery code. Server and device clocks must be synchronized.

Login and existing-account invitation acceptance both require the second factor when MFA is enabled. Password-only requests cannot create a session. Recovery codes provide 128 random bits each, are stored only as account-bound SHA-256 hashes and are consumed atomically in the login/invitation transaction. Failed password checks do not consume them. **Security** also lets you replace all recovery codes or disable MFA; both require the current password and a fresh authenticator/recovery code. Disabling MFA revokes all sessions. Rotation invalidates all old recovery codes but keeps existing sessions.

Security endpoints require an authenticated session, same-Origin POST and bounded authentication attempts. Settings changes revalidate the session inside the write transaction. Authenticator secrets, recovery codes, passwords and session hashes are excluded from workspace state and audit entries. Enrollment/recovery material is displayed in a temporary dialog and cleared when it closes; it is not written to browser storage. The provisioning URI is displayed as text and is not sent to a third-party QR service.

Authenticator secrets must remain recoverable for verification and are stored in the private SQLite database, not hashed. This implementation does not add application-level database encryption. Restrict server/data/backup access and use encrypted storage on the deployment host. Anyone with database access can compromise MFA. TOTP also does not provide phishing resistance. Deployment security review, authenticator-device acceptance and optional organization-wide MFA enforcement remain outstanding.

If both the authenticator and recovery codes are lost, the password recovery command alone cannot restore access. No public MFA bypass or automatic email reset is provided. Do not enable MFA until recovery codes are securely saved. The real owner account was not enrolled or modified during development; all lifecycle tests use temporary accounts.
