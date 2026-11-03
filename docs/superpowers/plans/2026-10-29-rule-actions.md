# Rich local automation rules implementation plan

Continue inline with TDD. Preserve keyword matching and first-match ordering, adding an optional saved contact segment and up to ten ordered local actions: draft, add/remove tag, assign member, set status, set custom attribute, internal follow-up task and final human handoff. Existing rules without action lists retain their draft behavior. No action changes campaign consent or sends externally.

Validate action shape, membership and source scope on save. Recheck live segment/member references before executing any action; missing dependencies block the entire rule and leave later rules eligible. Inbound webhook deduplication and one write transaction protect tasks/contact updates from duplicate delivery. STOP and human control continue to suppress rule execution.

- [x] Write failing action, segment, role/scope, removed dependency, replay and control tests.
- [x] Implement validation and atomic action execution with legacy compatibility.
- [x] Add a visual form for the supported action subset, preserving unsupported ordered configurations.
- [x] Run checks, document exact remaining gaps, update source package and local server.
