# ChatbotX adoption

Source revision: `abc0d4bcbfab3f77a558d7911536729aedbcebf8` of https://github.com/ChatbotXIO/ChatbotX.

The original MIT reference files and license are retained under `third_party/chatbotx`. No commercial enterprise code is included. These TypeScript references are not a second executable application: their patterns were adapted into VYBE's Python/SQLite security and tenant model.

## Delivered adaptations

* `business_hours.py`: weekly working intervals, date overrides/holidays, first-occurrence DST overlap handling and forward-transition gap handling. First accepted WhatsApp response targets use immutable schedule snapshots. Drafts, simulations and delivery-status upgrades do not count as replies. Human and automated accepted replies both count. Tracking starts after an administrator enables it; existing conversations are not backfilled.
* `google_connections.py`: separate encrypted Sheets/Calendar customer grants, offline authorization with PKCE, one-use state and a callback-specific secure cookie bound to the original administrator session. Refresh tokens remain in the credential vault. Disconnect removes the local grant without revoking other workspaces' grants.
* Sheets: preview/import up to 200 contact rows; name/phone headers required, no implicit consent and no overwrite of existing contacts. Explicit one-contact exports append plain values using RAW. Persisted write intent prevents blind retry after uncertain outcomes. Inspect unknown append outcomes in Google Sheets before making another request.
* Calendar: availability reads, explicit future bookings with deterministic Google event IDs, local/provider overlap checks, status reconciliation and cancellation. No invitations or attendees are sent. Concurrent changes made outside VYBE can still race with the availability check; Google calendars do not provide atomic slot reservations.
* `semantic_knowledge.py`: optional OpenAI embeddings and cosine similarity combined with lexical matching. Source/workspace filters and document digests reject disabled, deleted or stale passages. Batches contain at most 32 passages, queries have a one-hour tenant-scoped cache and raw query text is not stored in that cache. Semantic retrieval improves AI Ask; customer auto-replies still use lexical retrieval. OpenAI errors fall back to lexical grounding for Ask.

## Google platform setup (not yet configured)

1. In a Google Cloud project, enable Google Sheets API and Google Calendar API.
2. Configure the OAuth consent screen and the scopes used by this app: `openid`, `email`, `https://www.googleapis.com/auth/spreadsheets`, `https://www.googleapis.com/auth/calendar.events`, `https://www.googleapis.com/auth/calendar.events.freebusy`.
3. Create a Web application OAuth client. Add the exact redirect URI `https://vybe.srv1871828.hstgr.cloud/oauth/google/callback`.
4. Store `TW_GOOGLE_CLIENT_ID` and `TW_GOOGLE_CLIENT_SECRET` in the existing private server environment. Set `TW_GOOGLE_ENABLED=true`. Keep the existing credential-encryption key ring and public origin intact.
5. While Google's app is in testing, add authorized test users and account for Google's refresh-token expiry. Complete Google's applicable publishing/verification process before public customer authorization.
6. Restart the existing app. Customers use Settings → Google connections to authorize their own accounts; they never enter the platform client secret.

## Spending and acceptance

No model, embedding, messaging, payment or Google write requests were made to real providers during verification. Provider-bound paths use isolated contract tests, not fabricated production records. Semantic indexing/search remain disabled until a workspace administrator explicitly approves real embedding usage. Existing OpenAI/Meta real-usage settings are preserved on deployment.

Google Cloud credentials are not available yet, so live OAuth, Google reads/writes and public consent-screen acceptance remain unverified. Meta Tech Provider/App Review approval and existing calling/commerce/provider acceptance gaps are not resolved by these additions. Social channels, comments automation, realtime updates, weighted flow variants and MCP are separate future scope.
