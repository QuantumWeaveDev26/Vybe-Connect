# Knowledge and startup repair release

Implemented: guarded AI polling before application initialization; unsupported authentication templates are read-only and blocked from campaign sending; bounded text-PDF ingestion with existing tenant-scoped citations; explicit administrator approval for fetching a single public website page; public Terms route and accurate implementation status.

PDF limits: 1 MiB, 40 pages, 120,000 characters, isolated credential-free worker, eight-second timeout, Linux memory/CPU limits. Encrypted and scanned-image PDFs are rejected. Runtime initialization verifies real PDF extraction before starting the app.

Website ingestion remains HTTPS-only with public-address validation, pinned DNS, no redirects, no scripts/cookies, bounded responses and explicit approval. Sources remain disabled until reviewed. No full-site crawl or semantic retrieval is claimed. An actual local public-page fetch failed certificate-chain validation; TLS verification was preserved. Production external-fetch acceptance remains pending.

Verification: targeted Python contracts and deterministic JavaScript startup/template tests pass. Isolated REA mobile review at 390 x 844 showed PDF and website-permission forms without page errors. No production test records or paid provider calls were created.

Remaining: dedicated OTP editor/sender, Meta approval/onboarding acceptance, live AI inference acceptance, calling/audio acceptance, payment/shipping/subscription acceptance, recovery-email arrival, restore drill, full-site crawling/semantic retrieval, API writes/MCP and unimplemented WATI parity. Terms use the existing public brand; legal/provider identity review remains deferred.

## Deployment evidence

Runtime source: e5c0cda130eff6c942ad40997ef085201dc6f0f7. Archive SHA-256: ffc182a776df07136ffb01b2cf87f3f2da32b54a5bbfa726c72ff8c3671a274e. Hostinger action 123865406 succeeded: source initializer exited zero, one app healthy. Runtime logs confirm real bounded PDF extraction and credential-vault validation. Existing private configuration was preserved, with only TW_KNOWLEDGE_WEB_SELF_SERVICE=true added. Readback matches the deployed candidate exactly.

All 91 selected Python checks passed (90 in the combined run; the recovery HTTP check required tests on PYTHONPATH and passed separately). All 26 JavaScript suites passed. Eight public HTTP/security route checks passed; all 42 served JS/CSS assets match the pinned release byte-for-byte. Fresh public REA Chrome review at 390 x 844 completed sign-in rendering and password visibility with zero page errors. Earlier isolated authenticated REA checks covered the PDF and website-approval dialogs. This is browser-emulated mobile evidence, not physical-device or authenticated live-provider acceptance. No paid calls, messages, payments, shipments, inference or production sample records were used.
