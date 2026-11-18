# Keys-last readiness implementation plan

> Execute inline, using the existing Python service modules and unpaid isolated tests. Keep provider activation, payment and messaging off; preserve current production configuration.

**Goal:** Complete credential-independent launch preparation and a real backup restore drill, leaving only provider credentials, approval and live acceptance.

**Architecture:** Extend the existing private readiness command, plan catalog and backup utility. Reuse current subscription, Google, SMTP, AI and calling adapters; add no customer pages. Provider contracts are exercised with network transports replaced in isolated tests, never represented as live acceptance.

**Tech stack:** Python standard library, SQLite, existing cryptography vault, Node renderer tests, Docker/SSH deployment.

**Spec:** User request to implement pending services before supplying keys, with existing no-spend and current-theme constraints.

## Tasks

- [ ] Add failing tests for invalid AI allocations in billing plans, secret-free actionable setup diagnostics, and safe restore drills.
- [ ] Validate optional AI allocations and duplicate provider plan identities before checkout; expose only valid plans.
- [ ] Extend `readiness.py` with missing field names, activation gates and exact callback URLs without printing values or issuing network requests. Prepare a keys-last environment overlay with all live activation disabled.
- [ ] Extend `backup_data.py` with restore-drill verification, database row/integrity comparison, file checks and safe new-target handling. Test corrupted backups and links.
- [ ] Exercise every AI preset plus recovery, Google, subscription, commerce, call and permission workflows using the existing unpaid suites. Fix observed failures.
- [ ] Commit and push; deploy with existing environment/mount preservation. Run a private on-VPS backup and isolated restore drill during a brief app restart; restore no data into the running workspace.
- [ ] Verify live health and assets; report implementation separately from provider and physical-device acceptance.

## Review focus

- Placeholder credentials must not be called usable configuration.
- No configured service or simulated transport may be labeled live verified.
- Invalid plan limits, booleans and duplicate IDs must not silently grant a default paid allowance.
- Backup targets must not overwrite or follow symlinks into production data.
- Existing keys and customer data stay on the same server; no paid requests or new access grants.
