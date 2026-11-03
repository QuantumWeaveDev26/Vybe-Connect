# Credential-independent account recovery

The production audit confirms that browser password changes and forgotten-password recovery are missing. Add current-password-verified changes for the authenticated global account, revoking all its sessions across workspaces. Add a separate offline server-operator recovery command using getpass, never password arguments/environment/output. Recovery changes no role or membership. Preserve the actual local owner and database; verify only temporary accounts.

Account change is a same-origin, rate-limited authenticated HTTP endpoint. Use the existing PBKDF2 hash and fresh salt, transactional password verification/update/session revocation, audit every membership without secrets, and clear private UI state on success. Failed validation or a concurrent loser must not invalidate sessions. Recovery requires explicit offline confirmation and an existing account; it must not create a new database or account silently.

- [x] Add failing password, session, role isolation and concurrency tests.
- [x] Implement domain changes, protected HTTP endpoint and offline CLI.
- [x] Add scoped browser password form and release documentation.
- [x] Run full checks, package and preserve explicit production/parity gaps.

Verified locally: 404 tests passed in 164.484 seconds, Node UI/syntax and compilation passed, server/assets checked after restart. Container/TLS/live providers and full parity remain unverified. No real account password was changed.
