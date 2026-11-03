# Chatbot attachment and template delivery

The visual palette now supports **Send an attachment** and **Template message**. Both use the same durable checkpoint outbox as text: one provider submission at a time, advancing only after an accepted identifier. Draft/simulated runs produce unsent previews and make no transport calls. They do not produce fake delivery reports.

Attachment nodes select a workspace file previously uploaded through Inbox attachments. Uploading is a separate Meta operation; graph editing never uploads automatically. Current support follows the existing adapter: JPEG/PNG images, MP3/OGG audio, MP4 video and PDF documents, up to 5 MiB. Audio captions are rejected. Other captions support saved-variable substitution and must remain within 1,024 characters after expansion. Actual media replies require a real customer message within 24 hours and all live chatbot server gates.

Template nodes select a workspace template. Draft graphs can preview local/unapproved templates. Live configuration and execution require a synced Meta-approved template supported by the existing sender. Current body parameters are name/1 only; static text headers and supported static buttons remain available. Media/dynamic headers, carousels, dynamic buttons and arbitrary variables remain incomplete. This is a restriction of the current independent sender, not a claim that WATI lacks those formats.

Current customer consent is mandatory for template nodes. Approved templates can follow a persistent wait beyond the free-form service window. A following text/media node still checks the real window and will pause if it is closed. STOP and human control still cancel automation.

Each job freezes its resource snapshot, caption, recipient phone and template name parameter. The worker checks workspace ownership, resource availability/approval, snapshot identity, current phone, consent/window, admin ownership and graph version again. Changes cancel the old job; they never silently substitute a different attachment, template or recipient. Name and caption content use their queued snapshots. Meta can still reject expired provider media IDs; local resource checks do not prove remote availability.

Existing once-only claiming, unknown-result handling, late-provider reconciliation evidence and cancellation behavior remain. The latest delivery table reports message source, submission and recorded message status separately. Uploaded media links use the private authenticated endpoint. Resource access uses the existing authenticated workspace endpoints; source ZIPs contain no actual attachments, credentials or customer records.

REA static analysis of saved bot-action scripts returned parent Evidence `ev_8e5742546a00ab8a5fd9d59aad2787b8b6cde43fc70f62c6a2079fb8a8fdb265` and summary `ev_44ba5c8c4f335af4ad655aadb7077815267f41e8b4292fe2e99fd1d57cb4dd60`. Sources were parsed inertly. Unselected files and semantic retention limits leave application coverage partial. These artifacts inform the reconstruction but do not establish WATI backend/runtime equivalence. Live browser access remains unavailable.

Local tests use temporary files/databases and mocked upload/send transports. Real Meta acceptance, complete format coverage, exact WATI interaction and rendered visual parity are unverified. The full WATI goal remains active.
