# Rich chatbot delivery nodes

Continue the full active WATI goal by implementing visual media and approved-template graph nodes on the existing durable checkpoint outbox. Reuse the current official Meta adapters, not fabricated provider responses. All live gates remain disabled in the actual workspace.

Add `media` nodes referencing workspace-owned uploaded media, with bounded caption substitutions, and `template` nodes referencing local/synced templates. Draft graphs can preview local templates; live graphs require supported synced approvals. Freeze the resource snapshot, caption, recipient phone and template name parameter at enqueue. Recheck resource identity/approval and phone before submission. Media uses the real 24-hour window; templates require current consent and can send after a persistent wait outside that window. Later plain text still requires the real window. Questions and waits retain accepted-submission sequencing. No retries of unknown results.

Current adapter limits remain explicit: uploaded JPEG/PNG/MP3/OGG/MP4/PDF up to 5 MiB; no audio captions; template variables limited to name/1 and existing static header/button support. Missing/foreign/changed resources pause rather than silently substitute. No real upload is needed in draft mode if a resource does not yet exist: users can prepare text/template drafts, but actual uploaded-media selection waits for Meta configuration. The complete goal still includes broader media and template formats.

- [x] Add failing resource, adapter dispatch, snapshot, recipient, consent/window and simulation tests.
- [x] Implement resource resolution and schema/interpreter/outbox dispatch.
- [x] Add visual editors, preview and delivery source labels.
- [x] Verify regressions, package/restart and document remaining parity gaps.

Verification: 365 tests passed in 141.351 seconds, Node UI/syntax and Python compilation passed, restarted server HTTP assets verified. All real sending/AI gates remain false. Packaging retains independent source and fake tests only. Full WATI objective remains active.
