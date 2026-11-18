# Credential-independent launch preparation

The existing service modules remain the implementation. This release does not add customer pages, activate providers, change production keys, send messages or submit charges.

Changes:

- Subscription plans reject non-integer/out-of-range AI allowances and duplicate Razorpay plan IDs. Placeholder secrets no longer count as configured payment/shipping fields.
- The production environment example includes the agreed three plan definitions with empty provider IDs and disabled activation gates, plus platform AI and Google OAuth fields.
- Private readiness output identifies missing/invalid field names, disabled activation gates and callback URLs. It never prints keys or makes provider requests, and does not certify live acceptance.
- Recovery messages include Date, Message-ID and automatic-mail headers. A real TLS/SMTP loopback capture test verifies certificate checking and complete message receipt without sending external mail.
- The backup utility supports an isolated restore drill: exact file checksums, SQLite integrity/foreign keys, and separate credential decryption verification using the existing vault key ring. It refuses existing restore targets.
- `tools/acceptance_unpaid.py` runs each test module in a separate process with inherited provider settings removed and external TCP/DNS blocked. The manually invoked live-deployment script is excluded. It emits a machine-readable report.

Validation: 765 Python tests passed with one existing platform-specific skip, including every AI preset's foreground/queued adapter contracts, subscriptions and allowance controls, recovery, Google, calling, commerce and permission boundaries. Provider HTTP transports in those tests are simulated; the local SMTP test uses an actual TLS socket. A fresh read-only review found no blocking issues.

Deployment and the on-VPS restore drill are verified separately in private operational reports. Same-server backups do not establish off-host disaster recovery. Actual provider replies/payments/delivery, Meta approval, external mailbox placement and physical-device acceptance remain external gates; adding keys alone is not permission to spend money.
