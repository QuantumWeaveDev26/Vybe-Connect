# Knowledge and startup repair release

Implemented: guarded AI polling before application initialization; unsupported authentication templates are read-only and blocked from campaign sending; bounded text-PDF ingestion with existing tenant-scoped citations; explicit administrator approval for fetching a single public website page; public Terms route and accurate implementation status.

PDF limits: 1 MiB, 40 pages, 120,000 characters, isolated credential-free worker, eight-second timeout, Linux memory/CPU limits. Encrypted and scanned-image PDFs are rejected. Runtime initialization verifies real PDF extraction before starting the app.

Website ingestion remains HTTPS-only with public-address validation, pinned DNS, no redirects, no scripts/cookies, bounded responses and explicit approval. Sources remain disabled until reviewed. No full-site crawl or semantic retrieval is claimed. An actual local public-page fetch failed certificate-chain validation; TLS verification was preserved. Production external-fetch acceptance remains pending.

Verification: targeted Python contracts and deterministic JavaScript startup/template tests pass. Isolated REA mobile review at 390 x 844 showed PDF and website-permission forms without page errors. No production test records or paid provider calls were created.

Remaining: dedicated OTP editor/sender, Meta approval/onboarding acceptance, live AI inference acceptance, calling/audio acceptance, payment/shipping/subscription acceptance, recovery-email arrival, restore drill, full-site crawling/semantic retrieval, API writes/MCP and unimplemented WATI parity. Terms use the existing public brand; legal/provider identity review remains deferred.
