# Contact and conversation rule events implementation plan

Continue inline with TDD during the authorized hour ending 2026-10-29 12:01:55 UTC. REA parent evidence ev_4376299527698ac5aebbb60e39a14fa2db97e8587f851a196004339625725f28 recovered static RuleTypes names ContactCreated, ContactUpdated, AttributeIsAdded, AttributeIsChanged, ConversationOpened and ConversationResolved. Exact runtime semantics remain unverified.

Independent behavior: add triggers for manual contact creation/update, added/changed/removed custom attributes and explicit conversation open/solve transitions. Real inbound contact creation/open transitions can trigger rules after message/control validation. Simulations, CSV imports and mutations produced by rule actions do not recursively create these events. Human-held chats suppress events. First eligible rule per event uses existing priority/actions/segment checks. Attribute filters can target an exact field or any changed field. Preserve default incoming-message behavior and ensure non-message rules never match ordinary messages through an empty keyword.

Record bounded event/execution metadata for review, without raw message bodies or old attribute values. Event handling, actions, counts and source updates stay in the same transaction. No external actions or paid model calls.

- [x] Add failing event-change, filtering, replay, human-control, non-recursion and legacy tests.
- [x] Implement trigger validation, deterministic dispatch and source-operation hooks.
- [x] Add trigger selection, optional field filtering and recent execution history.
- [x] Run regression, update scope/package and restart locally before continuing.
