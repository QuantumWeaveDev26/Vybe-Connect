# Persistent drip execution

Implement inline with test-driven development. Replace configuration-only sequence definitions with up to eight ordered approved-template steps and waits. Drafting works without credentials. Explicit launch requires live configuration, approved templates, consent and a stable launch identifier. Snapshot templates and steps so later edits do not alter an active run. Reuse the durable outbound queue; gate each step on the preceding accepted submission, delay the next step from actual submission time, and stop later steps on a failed, unknown or skipped predecessor. Pause affects unsent rows, resume rechecks normal sending conditions, cancel never claims to recall in-flight messages. Provider delivery/read reports continue through existing signed webhooks. Keys remain deferred and tests use transport doubles.

- [x] Test launch gates, immutable snapshots, replay identifiers, timing, pause/resume/cancel, failure propagation and tenant/role boundaries.
- [x] Add drip_sequences.py and integrate queue eligibility and next-step timing.
- [x] Add a structured editor, launch review, run status and controls in drip-sequences.js.
- [x] Run checks and update the current release evidence and source package.

Local verification: 145 tests, JavaScript syntax, Python compilation and renderer/privacy checks passed. Provider transports were mocked; no live or paid calls occurred. Current visual acceptance, independent final review and complete WATI parity remain unverified.
