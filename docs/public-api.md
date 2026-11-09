# Public API and personal token management

Open Connectors → API tokens (the developer console, #developers). Workspace administrators can create named tokens with contacts:read, messages:read, analytics:read and/or messages:write permissions, choosing 7, 30, 90 or 365 days. The full bearer token is returned once, displayed in a private modal, and removed from the DOM on close, navigation, logout or workspace change. Save it in the integration's private secret store, not screenshots or source code. If creation completes after the dialog is dismissed, revoke the unseen token from the list and create another.

Only SHA-256 token hashes are stored. Management endpoints require a current administrator session and exact same-origin writes. Tokens are bound to their workspace and issuing administrator. Missing/expired/revoked keys, wrong secrets, missing scopes and removed/demoted administrators are rejected. Password changes/recovery and MFA enrollment/removal revoke the issuing user's tokens across workspaces. Demotion/removal permanently revokes their keys in the affected workspace, so promoting them later does not revive old access. Logout alone does not revoke integration tokens. Administrators may revoke any key within their current workspace. Revocation blocks subsequent requests; a request already authenticated can finish.

## Requests

Base: https://vybe.srv1871828.hstgr.cloud/api/v1

Send `Authorization: Bearer YOUR_PRIVATE_TOKEN`. Session cookies and query-string tokens cannot authenticate these endpoints. X-Workspace cannot override the token's workspace. All responses use no-store and HTTPS is required in production. Each token allows 60 authenticated resource requests per minute. A persistent per-token minute budget returns HTTP 429 after the limit; retry next minute. Scope failures return 403; invalid credentials return 401.

- GET /contacts — contacts:read. Returns contact ID, name, phone, tags, attributes, optin, status, assignee and available created/updated fields. Internal runtime fields are omitted.
- GET /messages — messages:read. Returns recorded inbound customer messages and outgoing accepted/sent/delivered/read/failed/unknown/sending messages. Internal notes, drafts and simulations are excluded. Optional contact_id restricts to one contact in this workspace.
- GET /analytics?from=2026-11-01&to=2026-11-05 — analytics:read. Uses the existing recorded-traffic report and its UTC/date validation, not simulated metrics.

Contacts/messages accept limit (1–100, default 50) and after (a numeric cursor returned as next_after). Pass the returned cursor unchanged until it is null. Lists read current records, not immutable snapshots. Analytics dates span at most 366 inclusive days.

Read scopes cannot send messages or change records. The opt-in messages:write scope permits POST /api/v1/messages/send with a JSON phone and body. It requires an existing contact, a current 24-hour WhatsApp service window, live sending enabled, and the same entitlement and provider checks as the inbox. It returns actual provider acceptance, or an explicit failure/unknown result; it never invents a send. Interactive buttons are rejected until a real adapter is available. No provider retries are automatic. Create campaigns, contact mutation, private attachments, AI and billing remain outside this API. WATI's complete public API/MCP compatibility is not claimed. Existing signed agent callbacks remain separate.

## Verification

89 Python tests passed across token security, actual HTTP management/Bearer flows, existing webhook routes, membership, password, MFA and recovery. All 25 JavaScript suites passed, including show-once cleanup and stale-workspace fencing. REA isolated headless Chrome completed creation, selected permission, secret reveal, close and revocation; the final screen showed Revoked with no secret. No production token, synthetic customer account in production, paid AI call, WhatsApp message, call, payment or shipment was created during acceptance.

API metadata is included only for current workspace administrators; public review contexts have no active session and receive no token metadata. Names are escaped in the UI. Audit logs record creation/revocation IDs without token secrets. A maximum of 25 unexpired, unrevoked tokens may exist per workspace. Active keys remain visible first in the last-100 metadata list.

## Deployment evidence — 5 November 2026

Source 10dc705ac18afa7d4982127d84affa55d5523e0b, archive SHA-256 f98b8e5c4f02efadd773d1dc8c37e1ddfe1a68a3d4c859437ba81999df061a57, Hostinger action 123857261. Exactly one app container is healthy; the initializer exited zero. Root and the four changed public assets match the committed release; all 42 versioned asset references have matching content hashes. Health and readiness return 200; anonymous state, token-management and all three public API endpoints return 401; source/.env paths return 404. Private deployment environment readback exactly matches the previous environment. No production API token was created for testing.

REA checked the creation/secret dismissal/revocation cycle at 1440x1000 and the token form at 390x844, using an isolated temporary workspace. No page errors were recorded in the complete desktop scenario. These are controlled headless browser checks, not physical-device acceptance. Remaining work includes public API write/send endpoints, advanced reports, number registration/coexistence, Meta approval and live-provider acceptance. No paid tests ran.
