# Customer WhatsApp connection

The platform app is `1495048929178011`; the WhatsApp Embedded Signup configuration is `1103788759165502`. The earlier General configuration is not used. Customers use email/password to enter VYBE Connect, then Facebook Login for Business specifically to authorize their WhatsApp assets.

## Implemented

Workspace administrators can prepare a signup attempt, then click Continue with Meta to launch the official JavaScript SDK. Code and account/number selection return through the SDK and trusted Meta origins. The server consumes a short-lived, session/user/workspace-bound nonce, exchanges the single-use code, checks app identity and both required scopes, verifies phone membership, subscribes a workspace-specific callback override and confirms that subscription before activation. Another workspace cannot claim the same WABA/number or the operator's existing configured account. Slow provider requests do not hold the global database write lock.

Customer credentials are private server files under `TW_DATA_DIR/meta-credentials`; directories use 0700 and files 0600 on Linux. No raw tokens are stored in entity JSON or returned by application state. These files are not cryptographically encrypted by the application: encrypted host storage/backups and restricted operator access are still required. Keep them out of source control, public mounts, logs and exports. Platform App Secret and webhook verification secret stay in server environment variables.

Sending starts paused. A separate administrator confirmation enables actual business sending and discloses possible Meta charges. Authorization expiry pauses sending and shows reconnect required. Disconnect removes the local credential and stops local incoming processing/sending; it does not revoke Meta's grant remotely. Customers can revoke that grant in Meta Business Integrations. Reconnection pauses existing sending until explicitly enabled again.

## Configuration

Set `TW_META_PLATFORM_ENABLED`, `APP_ID`, `CONFIG_ID`, `APP_SECRET`, `VERIFY_TOKEN` and `VERSION` as documented in `.env.production.example`. Public SDK configuration exposes only the app/configuration IDs and Graph version. Add the deployed domain to the Meta app's website/JavaScript SDK allowed-domain settings as required by the dashboard. SDK scripts/frames are allowed only for explicit Meta hosts when the feature is configured. Existing operator-provisioned workspaces retain their scoped configuration until explicitly reconnected.

## Acceptance still pending

- Actual SDK popup, returned authorization and account connection in a browser; Meta may limit use to app-role users until required access is approved.
- App Review screencasts, messaging API requirement and approval for external businesses. Creating a configuration or publishing the app is not approval.
- Number eligibility, registration and migration/coexistence acceptance. This increment does not automatically register new numbers, migrate a WATI number or change its registration PIN.
- Multi-number workspaces (currently one number and one WABA per workspace), remote grant revocation, automatic token renewal, and encrypted application-level credential storage.
- A dedicated reviewer account and actual recorded reviewer workflow.

No live OAuth exchange, provider subscription, message, call or paid AI invocation was run during automated tests. The full Python suite passed 575 tests (one POSIX permission check skipped on Windows), followed by 14 focused signup tests and 30 HTTP tests after final changes. JavaScript route/rendering and signup event-isolation tests passed. Local visual acceptance was blocked by disabled local-browser access.
