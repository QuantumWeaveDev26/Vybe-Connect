# Received WhatsApp attachments

Signed inbound webhooks persist attachment metadata once per message. The inbox displays images, audio, video and documents as received records. A teammate explicitly retrieves a file from Meta; there is no automatic provider download. Simulated events do not create real received attachments.

Retrieval first requests media metadata from the configured Graph version with the workspace phone_number_id, matching [Meta's official Retrieve Media URL request](https://www.postman.com/meta/whatsapp-business-platform/request/ptjyi84/retrieve-media-url). Main Meta documentation was unavailable/429 during implementation. The adapter's remaining metadata/download contracts are locally tested and still require live verification.

This initial implementation accepts only HTTPS lookaside.fbsbx.com attachment paths returned by the metadata call. Other CDN destinations fail closed; this restriction does not claim that Meta uses only this host. Public DNS/TLS pinning, disabled redirects/proxies, bounded response bytes/time, MIME/file-signature checks and SHA-256/size verification protect publication. Signed URLs and access tokens are never persisted or exposed to the browser. Supported subset: JPEG, PNG, MP3, mono Opus OGG, MP4 and PDF, maximum 5 MiB. Format checks are not malware scanning.

Files use the existing workspace-private media store and authenticated local download route. Completed retrievals reuse the stored asset; failures and expired retrieval claims require explicit retry. Publication rechecks current membership and the claim. Received assets stay out of the outbound upload picker. Image/audio/video controls reference only the local private asset; PDF/file links use the same authenticated route.

Non-text messages pause automation and request human review. Active chatbot sessions are stopped and pending customer AI answers are discarded. This build does not inspect, transcribe or summarize attachment contents with AI. Calls, stickers, other document/audio formats, larger files, automatic retention/cleanup and full WATI media behavior remain incomplete.

Checks use temporary local databases and provider transport doubles. No live Meta retrieval, paid AI request, upload or WhatsApp send occurred during verification. Browser/device playback and current visual parity remain unverified.
