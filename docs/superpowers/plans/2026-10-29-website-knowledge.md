# Website knowledge implementation plan

Continue inline with TDD. This is a single public-page ingestion and explicit refresh increment, not complete crawling or semantic training. Existing Python/SQLite document chunks and passage citations remain the retrieval contract.

Administrators add a public HTTPS URL on an exact server-allowlisted origin. Resolve only public addresses and pin the TLS connection; no cookies, credentials, query strings, fragments, redirects, proxies, scripts, linked resources or private targets. Limit one response to 1 MiB and extracted text to 120,000 characters. UTF-8 HTML and plain text only. Strip executable/non-content HTML. Fetch outside SQLite write transactions, then check a revision before atomic chunk replacement. A failed refresh retains the last successful snapshot and reports a sanitized error. New sources default disabled pending review. Existing enable/delete and customer-source approval controls continue to apply.

- [x] Write failing transport, extraction, membership, scope and refresh preservation tests.
- [x] Implement bounded HTTPS fetch, source CRUD/refresh and existing retrieval integration.
- [x] Add website add/preview/refresh controls and last-fetch/error metadata.
- [x] Run regression and renderer checks, update feature boundaries, package and restart. Mock all website fetches; no paid AI or provider sends.
