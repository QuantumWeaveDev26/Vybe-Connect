# Finish private provider setup

The application, adapters and unpaid acceptance runner can be prepared before provider keys exist. This file is operator guidance, not a customer page or a live acceptance certificate.

## Private configuration

Use `.env.production.example` as a field reference. Do not replace an existing production `.env` with this example: preserve the existing credential key ring, recovery secret, setup token, data paths and configured providers. Enter real values only in the private server environment, never Git or chat.

- Razorpay: activate the merchant account and Subscriptions, create the three real INR monthly plans, and put their verified IDs into `TW_BILLING_PLANS`. The proposed prices are ₹499/₹999/₹1499 with 50/150/300 AI requests. Invalid allocations and duplicate provider plan IDs are rejected. Platform subscription credentials are separate from each merchant's order-payment credentials.
- Google: create a web OAuth client, enable Sheets and Calendar APIs, and register the exact `/oauth/google/callback` URL shown by `python -B readiness.py`. Customers then authorize their own account. Existing vault keys encrypt their refresh tokens.
- Meta: retain the existing platform app and complete its Tech Provider/permission approval. Customers authorize their own account through the existing connection flow. Configuration alone does not establish approval or message delivery.
- AI: the platform supplies the OpenAI key. Customers use their subscription allowance and do not supply a model key. Quota, model access and live reply quality still need acceptance after the provider is ready.
- Recovery: use a verified sender and TLS SMTP credentials. Local certificate-verified SMTP delivery is tested; check actual mailbox delivery separately.
- Calling and commerce: keep the existing per-workspace activation gates off until an explicitly approved provider test. Public customer authorization, eligible WhatsApp calling, TURN connectivity, payment capture/refund and shipping acceptance cannot be established by static configuration.

`python -B readiness.py` prints missing field names, disabled activation gates and callback URLs without values or network requests. Its exit status remains 2 until live acceptance is established externally. Adding keys does not itself authorize charges; leave live gates disabled until approval.

## Unpaid verification

Run `python -B tools/acceptance_unpaid.py --output PRIVATE_REPORT_PATH`. It strips inherited provider settings, blocks external TCP/DNS, uses isolated local stores and excludes the manually invoked live-deployment script. Provider transports used by tests are simulated and are never labeled real provider acceptance. The local recovery SMTP test uses a temporary trusted certificate and captures mail on loopback only.

## Backup and recovery

Stop only the VYBE application while taking a consistent data-directory backup; keep the source, environment and credential key ring separately protected. Run:

```
python -B backup_data.py backup --source PRIVATE_DATA_DIR --target NEW_PRIVATE_BACKUP_DIR --offline-confirmed
python -B backup_data.py drill --source PRIVATE_BACKUP_DIR --target NEW_ISOLATED_RESTORE_DIR
```

The drill validates file checksums, SQLite integrity and foreign keys in a new directory. It refuses an existing target and never swaps production data. `backup_data.verify_credentials(restored_directory)` additionally decrypts restored credential files using the separately supplied current/retired vault keys; it returns counts only. Keep backup copies private and restart the original app after the drill. A same-server backup/drill does not provide protection against losing the entire VPS; copy encrypted backups to a separately approved destination for that protection.

## Remaining external acceptance

Real subscription authorization/renewal/cancellation, all-agent live model replies, Meta onboarding/message delivery, real call audio, payment/shipping operations, mailbox delivery and physical-device testing remain separate acceptance tasks. No simulated success, hidden setup error or claim of complete WATI/Emovur parity substitutes for these results.
