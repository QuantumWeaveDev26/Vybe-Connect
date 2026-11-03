# Website knowledge

Wati AI → Knowledge → Add website page indexes one public UTF-8 HTML or plain-text page. The workspace administrator supplies a title and direct HTTPS URL. On the local server, set TW_KNOWLEDGE_WEB_<UPPERCASE_WORKSPACE_ID>_ALLOWED_ORIGINS to comma-separated exact origins, then restart. An empty allowlist blocks fetching. Never add credentials or signed/private URLs.

The fetcher accepts HTTPS on port 443 without credentials, query strings or fragments. It verifies public DNS addresses and pins the TLS connection to a checked address while validating the hostname. It sends no browser cookies or authorization, follows no redirects, uses no proxy, executes no scripts and fetches no linked resources. Responses must be HTTP 200, uncompressed HTML/plain text, up to 1 MiB. Read time and extracted character count are bounded. JavaScript-rendered pages and non-UTF-8 content may not provide usable text.

New website sources remain disabled until reviewed. Review snapshot shows up to the first three indexed passages; it identifies truncated previews. Enable makes the source available to staff AI retrieval. Customer support assistants additionally require selecting it among approved sources. Source text remains untrusted reference material, never authorization to invoke tools or change records.

Refresh page performs an explicit fetch of that same URL. The fetch occurs outside the database write transaction. A successful refresh atomically replaces passages, preserves enablement and retains the source identifier. An in-flight source change, deletion or administrator-access change prevents replacement. A failed refresh records a sanitized error and preserves the last successful snapshot. There is no automatic refresh schedule in this increment.

Website pages and uploaded documents share the existing twenty-source quota, local lexical retrieval and passage citation contract. Refreshing invalidates old passage identifiers; prior chat answers remain in history, while old passage links may become unavailable. A customer answer using an older snapshot is discarded when publication detects the source change.

This is single-page ingestion, not full-site crawling, sitemap discovery, semantic/vector search, PDF extraction or complete WATI training parity. Automated tests mock website transport. Actual website compatibility, live model grounding quality and current browser visuals remain unverified.
