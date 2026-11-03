# Deployment package and release gates

This checkout now has an explicit HTTPS reverse-proxy boundary, Secure production cookies, protected first-owner setup, health/readiness routes, a non-root single-instance container definition, persistent private storage and offline backup/restore tools. **The complete product is not yet verified ready for production clients.** Docker is unavailable on the development computer, so the image, Compose startup and public TLS have not been exercised. The requested respond.io/SleekFlow/Interakt additions and full WATI parity remain tracked in docs/competitor-adoption.md.

## Intended topology

One app container behind Caddy, with only proxy ports 80/443 published. The app keeps SQLite, uploads and knowledge files in a persistent named volume, normally `/var/lib/teamwave/active`. Do not scale the app to multiple replicas or place SQLite on a network filesystem. This topology needs load testing and operational acceptance before client onboarding. The Python HTTP server has bounded request sizes, socket timeouts and origin/authentication controls; it is not a claim of a complete high-scale service platform.

The reverse-proxy configuration follows [Caddy's official reverse-proxy documentation](https://caddyserver.com/docs/quick-starts/reverse-proxy). A real domain must point to the deployment host and reach its proxy. No domain, certificate, hosting or provider purchase was made here.

## Prepare on the deployment host

Keep a real production environment file outside source control, with restricted access. Copy `.env.production.example` as a starting point and replace the origin and setup token. Generate a random token, for example with `python -c "import secrets; print(secrets.token_urlsafe(48))"` in your own terminal; do not paste it into chat. The shipped placeholder is rejected for a fresh installation. Keep all Meta LIVE/FLOW_SEND and AI/paid/automatic-reply flags false until an approved live test. Add the exact workspace variables only after setup.

Use an exact origin such as `https://chat.your-domain.com`, with no path/query/fragment/credentials. Production mode refuses invalid origin configuration and fresh setup without a sufficiently long token. The setup form asks for that token once; it is not stored in browser storage. Existing initialized owner accounts remain required and unchanged. Current-password changes and offline server-operator recovery are implemented; optional authenticator MFA and single-use recovery codes are implemented locally. Self-service email recovery and deployed/device MFA acceptance remain outstanding. See docs/account-security.md.

On the deployment machine with Docker/Compose installed, from this source directory, set `TW_ENV_FILE` to the absolute path of the private environment file and use that same file for Compose interpolation:

```sh
docker compose --env-file /private/teamwave.env config --quiet
docker compose --env-file /private/teamwave.env build
docker compose --env-file /private/teamwave.env up -d
docker compose --env-file /private/teamwave.env ps
```

Do not print the expanded Compose configuration: it can contain secrets. The private environment file must contain `TW_ENV_FILE=/private/teamwave.env` (adjust both paths). The image build excludes `.env*`, runtime data, databases, captured artifacts and archives. Containers receive credentials through environment variables rather than source files.

## Required host acceptance

- Build/start the image and verify non-root access to the data volume.
- Check real `https://YOUR_DOMAIN/healthz` and `/readyz`; inspect valid HTTPS and Secure cookies in the browser. Readiness proves database access, not full product/provider health.
- Confirm owner login, workspace isolation, source/private-media access and rejection of another Origin/Host through the actual proxy.
- Confirm live provider gates remain false until deliberate approval.
- Run an offline backup/restore drill and verify restored media, contacts and login.
- Verify signed Meta webhook setup and approved OpenAI/Meta/commerce tests after credentials are supplied.
- Finish the product feature, access/recovery, device/browser, load and operations checks before onboarding clients.

Current authentication budgets are thread-safe: 12 attempts per address/account identifier per minute and 120 per source address overall. Forwarded client-IP headers are intentionally not trusted, so proxy clients share the broader budget. External edge protection, monitoring and reset-proof distributed limits remain deployment responsibilities; no paid service is configured automatically.

## Offline backup and restore

Stop the app before copying private data. `backup_data.py` produces a consistent SQLite copy plus private files and a SHA-256 inventory, refuses links/junctions and never overwrites a target. The inventory detects accidental changes; it is not an authenticated or encrypted backup. Protect backups like the live database. No real customer backup was created during testing.

Example on a Linux deployment host: create a private backup directory writable by container UID 10001, then stop `app` and run the tool through an ephemeral container. Use a new dated target every time:

```sh
docker compose --env-file /private/teamwave.env stop app
docker compose --env-file /private/teamwave.env run --rm --no-deps -v /srv/teamwave-backups:/backups app python backup_data.py backup --source /var/lib/teamwave/active --target /backups/2026-11-02 --offline-confirmed
docker compose --env-file /private/teamwave.env up -d app
```

For restore, stop the app and restore into a new directory such as `/var/lib/teamwave/restored-2026-11-02`. Do not overwrite the active directory. Change `TW_DATA_DIR` in the private environment file to the restored directory and restart the app, then verify records and attachments before accepting traffic. Retain the old directory for recovery. Secret environment variables and Caddy certificate state require separate protected backups; the application-data tool does not back them up.

No deployment or public release has been performed from this chat.
