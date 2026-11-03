# Shopify connector contract

`shopify_connector.py` uses only Python standard library. It executes fixed read-only Admin GraphQL queries, never mutations, order creation, payment operations, webhook registration, or retries. Importing it and checking status never contact Shopify.

## Configuration

For tenant `demo`, configure server environment variables (never send them to the browser):

```text
TW_SHOPIFY_DEMO_SHOP=your-store.myshopify.com
TW_SHOPIFY_DEMO_TOKEN=<Admin API access token>
TW_SHOPIFY_DEMO_API_VERSION=2026-10
TW_SHOPIFY_DEMO_WEBHOOK_SECRET=<Shopify app client secret>
```

The prefix is `TW_SHOPIFY_<UPPER_TENANT_ID>_`. Tenant IDs must contain only ASCII letters, numbers or underscores, 1–64 characters. Do not replace punctuation with underscores: that could alias separate workspaces. Shop configuration is an exact lowercase `single-label.myshopify.com` hostname. URLs, ports, paths, credentials, custom domains, subdomains and IPs are rejected. All transport uses HTTPS to that validated host; redirects and environment proxy forwarding are disabled.

The version must be explicitly set to a quarterly `YYYY-01`, `YYYY-04`, `YYYY-07` or `YYYY-10` release. Official Shopify references showed `2026-10` as latest when checked on 2026-10-29. Configuration format alone does not prove a version is still supported. Every successful response must include `X-Shopify-API-Version` equal to the requested version; silent provider fall-forward is rejected as `api_version_mismatch`. Consult [Shopify versioning](https://shopify.dev/docs/api/usage/versioning) when selecting/upgrading a version.

Minimum scopes are `read_products` and `read_orders`. Order access normally covers the last 60 days; older orders require approved `read_all_orders` access. This adapter needs no write scopes. Customer fields (email, phone, address) are not requested. Provider app approvals/access restrictions can still prevent reads. See [Product access](https://shopify.dev/docs/api/admin-graphql/latest/objects/Product) and [Order access](https://shopify.dev/docs/api/admin-graphql/latest/objects/Order).

## Python API

- `connector_status(tenant)` returns `configured`, safe `shop` and `api_version`, `webhook_configured`, `read_only: true`, `required_scopes`, and `live_verified: false`. These flags report settings only, never successful provider authentication.
- `fetch_products(tenant, limit=25, cursor=None)` fetches one page. Limits are integers 1–50 (booleans rejected); cursor is `None` or a nonempty string of at most 2048 characters.
- `fetch_orders(tenant, limit=25, cursor=None)` uses the same paging contract. Queries are GraphQL read queries over HTTP POST, with variables for cursors.
- `verify_shopify_webhook(tenant, raw, headers)` returns a boolean; `raw` must be the original unmodified `bytes`, and headers a mapping containing the full `X-Shopify-Hmac-SHA256`, `X-Shopify-Shop-Domain` and `X-Shopify-Topic` names (case insensitive).

Successful fetch result:

```json
{"ok":true,"items":[],"page_info":{"has_next_page":false,"end_cursor":null},"shop":"your-store.myshopify.com","api_version":"2026-10","error":null}
```

`page_info` reflects actual provider `pageInfo`, including its cursor on the final page. Caller must explicitly request each next page and decide storage/refresh policy. Products contain `id`, `title`, `handle`, `status`, `updated_at`. Orders contain `id`, `name`, `created_at`, `financial_status`, `fulfillment_status`, and `total_price: {amount, currency_code}`. Money stays a decimal string. Unknown fields and customer PII are discarded.

Failed fetches always contain `ok:false`, `items:[]`, `page_info:null`, and `error:{code,retryable,http_status}`. They do not return raw provider error messages or partial GraphQL results. Codes include `invalid_input`, `not_configured`, `network_error`, `unauthorized`, `rate_limited`, `redirect_blocked`, `provider_error`, `http_error`, `graphql_error`, `response_too_large`, `api_version_mismatch`, and `invalid_response`. Only network, HTTP rate limiting, and HTTP server failures are marked retryable. There is no automatic retry, sleep, or cost-consuming follow-up. Request timeout is 15 seconds; provider responses and webhook bodies are capped at 2 MiB. Transport/error paths do not log tokens or response bodies.

The [products](https://shopify.dev/docs/api/admin-graphql/latest/queries/products) and [orders](https://shopify.dev/docs/api/admin-graphql/latest/queries/orders) query documentation defines the provider connections and cursors used here.

## Webhook boundary

The verifier computes HMAC-SHA256 over the exact raw bytes using the configured app client secret, strictly decodes the base64 header, and compares digest bytes in constant time. It requires an exact configured shop match and a topic in `WEBHOOK_TOPICS` (product create/update/delete; order create/updated/cancelled/paid/fulfilled/partially_fulfilled/delete). Missing configuration or malformed input returns false. A webhook secret and shop can verify deliveries even when API token/version are not configured.

The Shopify signature authenticates the body, not the topic/shop headers themselves; never interpret it as an authenticated freshness timestamp. Verification alone does not prevent replay. The server must authenticate tenant association, reject invalid signatures before parsing, deduplicate `X-Shopify-Webhook-Id` deliveries durably within the tenant/shop, cap HTTP bodies before reading, and accept only expected resource schemas. Dispatch only allowlisted topics. The verifier neither creates local orders nor sends WhatsApp messages. [Shopify verification guidance](https://shopify.dev/docs/apps/build/webhooks/verify-deliveries) explains raw-body HMAC and duplicate handling.

## Evidence and limitations

Tests use synthetic data and mocked urllib transport only:

```powershell
python -m unittest discover -s tests -p test_shopify_connector.py -v
```

No credentials, live Shopify calls, paid services, installations, orders or payments were used in development. Passing tests prove local request/response validation and signature contracts, not installed-app scopes, live schema compatibility, provider connectivity, webhook delivery or end-to-end sync. The host application's authenticated sync, storage, audit, webhook deduplication and UI are separate integration responsibilities.
