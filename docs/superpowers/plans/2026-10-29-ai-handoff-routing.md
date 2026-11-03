# AI handoff routing implementation plan

Continue inline using TDD and existing Python/SQLite architecture. User requests complete functional parity with credentials last. This increment adds independently implemented support routing; exact WATI routing semantics remain unverified.

Preserve an existing valid conversation assignee. Otherwise route to a configured workspace member, falling back to the assistant administrator if membership changed. Optional internal follow-up tasks default off and use the same assignee. Store bounded internal reason, job and timestamp on the contact; do not include these in customer model context. Apply the same routing to explicit handoff, unusable output, uncertain sends and interrupted worker recovery. Resume marks the handoff resolved, retains history and allows future messages; it does not replay stopped jobs or send messages.

- [x] Add failing scope, routing, task, recovery and resume tests.
- [x] Implement shared transactional handoff helper, configuration validation and worker integration.
- [x] Add configuration and escaped inbox handoff details.
- [x] Run regression and renderer checks, update source package and local server without paid calls.
