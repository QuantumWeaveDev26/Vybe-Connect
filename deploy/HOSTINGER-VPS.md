# VYBE Connect: live Hostinger installation

Live URL: https://vybe.srv1871828.hstgr.cloud

Deployed 3 November 2026 to VPS 1871828 as Docker project `vybe-connect`. This is separate from the empty Business hosting destination. The existing `n8n` and `aicampus` projects were not modified. The installation reuses their external `n8n_default` proxy network and existing Traefik certificate resolver. No DNS changes, hosting purchases or provider calls were needed.

## Complete first-owner setup

1. Open Hostinger hPanel, VPS, this server, Docker Manager, project `vybe-connect`.
2. In the private project environment, copy `TW_SETUP_TOKEN`. Keep it out of chat and Git.
3. Open the live URL and enter that token with your own owner email and a strong password.
4. Verify login and workspace access. Configure provider credentials only in private server environment variables. Keep paid/live/automatic-send gates disabled until an explicitly approved provider test.

No owner account or password was created on your behalf. The initial database is fresh; local customer data, credentials and captures were not uploaded.

## Configuration and source

`hostinger-vps.compose.yaml` is the deployed manifest with an environment-variable placeholder for the private setup token. Do not print the expanded Compose configuration or commit its private environment. The initializer source is `hostinger_source_init.py`; its base64 form is embedded in the manifest to avoid a remote Docker build dependency. If changing the initializer, regenerate that command from the reviewed file.

Application commit: `363df7d7695d7a6a2c5064b3eecf8964be0c9f60`.

Source ZIP SHA-256: `013d38cdf3fea692e1cb086ffa328c1c84c75cd345b32845dfb0f4f3c4c5c9c6`.

The one-shot initializer validates the GitHub archive digest and archive paths before installing the source into `app_source`. A matching cached release avoids a download on later starts. The app mounts this source read-only and runs as UID/GID 10001. Its private SQLite/uploads/knowledge data is in `app_data`, under `/var/lib/teamwave/active`. Never remove these volumes during an update. The Python base image currently follows `python:3.13-slim`; source pinning does not pin that base image digest.

Git pushes do not auto-deploy this project. For an application update, first test the new commit, update the initializer commit/digest and the manifest source paths, regenerate its embedded command, then update only `vybe-connect` in Docker Manager. Keep a protected backup and the previous manifest/source release. Never restart the whole VPS or change the shared proxy merely to update this app.

## Verified evidence

- `vybe-connect-source-init-1` exited 0; app container is running and healthy.
- Trusted public HTTPS: `/`, `/healthz`, `/readyz`, `/api/bootstrap`, `/help-widget.js` and `/vybe-theme.css` return 200.
- Root HTML identifies VYBE Connect and includes CSP and HSTS headers.
- `/api/state` without login returns 401, `/.env` returns 404, and owner setup without its token returns 403.
- Bootstrap reports hosted deployment, token-required fresh setup, and password recovery disabled.
- Existing n8n, Traefik and AI Campus containers remain running.
- AI, SMTP recovery and sandbox gates are disabled; no live provider transaction was performed.

This is deployment and HTTP evidence. Browser/device acceptance is pending because browser use was disabled by the local Work setting. Full WATI parity, calling/commerce/onboarding/billing completion, deployed owner/MFA lifecycle, live Meta/OpenAI/webhook acceptance, backup/restore drills, load tests, monitoring and operational sign-off remain outstanding. Do not onboard production clients based solely on these health checks.

The 3 November agent-directory update was deployed from the commit above after 483 Python tests, Node renderer/privacy and directory checks, and authenticated local demo browser checks. The local demo database and its example configurations are not part of the hosted installation.

The token-free public review increment is enabled using `TW_PUBLIC_REVIEW=true`. The homepage opens an isolated, read-only sample workspace; owner setup/sign-in is at `/owner`. Review writes and provider execution are blocked. Set the flag false after interface acceptance. See `docs/public-live-review.md` for isolation and validation details.
