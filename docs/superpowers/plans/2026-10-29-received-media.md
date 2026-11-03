# Received WhatsApp media implementation plan

Continue inline with TDD. Signed inbound events persist supported attachment metadata once per message, without automatic downloads. Non-text messages request human review and stop active graph/AI continuation; this build does not inspect media content with AI. Staff explicitly retrieves a received attachment by its tenant-scoped record, never an arbitrary supplied URL or Meta ID.

Implement a read-only two-step adapter: retrieve metadata from the configured Graph version with phone_number_id, then download the short-lived URL. This initial transport accepts only the exact lookaside.fbsbx.com HTTPS attachment path; other hosts fail closed. Pin public DNS/TLS, disallow redirects/proxies, bound response bytes/time, validate MIME/file signatures and SHA-256/size. Support the existing 5 MiB JPEG/PNG/MP3/mono Opus OGG/MP4/PDF subset. Keep provider URLs/tokens out of persistence and client state.

Claim explicit downloads transactionally, store files in the existing private media directory and recheck membership/claim before publication. Repeated completed downloads reuse the private asset; failures require explicit retry. Received files are excluded from the outbound upload picker. Browser shows local received attachment controls/previews only. No automatic paid/provider operations during testing.

Reference: Meta's official Postman Retrieve Media URL request confirms GET graph.facebook.com/<version>/<media-id>?phone_number_id=<phone>. Main Meta documentation was unavailable/429 during this run. Remaining response/download contracts require live verification; restricted CDN support is an independent implementation constraint, not a claim about all Meta media hosts.

- [x] Add failing metadata/replay, scope, human-control, download reuse/error and transport-validation tests.
- [x] Implement bounded provider retrieval plus private transactional asset publication.
- [x] Add received attachment state and inbox controls without exposing provider URLs.
- [x] Run transport/domain/HTTP/renderer checks, document limits, package and restart.
