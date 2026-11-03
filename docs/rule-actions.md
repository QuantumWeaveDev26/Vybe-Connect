# Local rule actions

Rules match an inbound keyword and, optionally, a saved contact segment. Lower priority numbers run first; equal priorities retain creation order. The first eligible matching rule consumes the event before keyword chatbots or customer AI. A missing saved segment or assignee blocks the entire rule rather than widening its audience or applying only some actions. Later rules remain eligible.

Each rule supports up to ten ordered actions: add/remove tag, set a text custom attribute, assign a workspace member, change chat status, create an unsent draft, create an internal follow-up task and final human handoff. Draft text supports {{name}}. Handoff must be last, marks Pending and holds automation. These actions do not alter campaign consent, send messages, invoke AI, call webhooks or contact external services.

Membership, dependency and contact capacity checks run before writes. The contact retains at most 25 tags and 50 custom attributes within its existing JSON size limit. Replay protection uses the inbound message's existing unique workspace/provider identity; contact updates, drafts and tasks are committed in the same transaction. STOP and human takeover suppress rule execution. Tasks are internal records with no email or WhatsApp notification.

The visual form supports one of each action in its displayed order. Repeated or custom-ordered API configurations retain their action sequence when editing rule settings, rather than silently rewriting it. Existing keyword-draft rules remain supported, including edits to their implicit draft text.

This is an independently implemented subset of WATI rules. No-response triggers, calls/social-channel triggers, starting chatbots/AI agents/drips from rules, live template actions, advanced execution policies and exact WATI operator/UI parity remain incomplete.

## Contact and conversation events

Rules can also trigger on manual contact creation/update, added/changed/removed custom attributes and explicit conversation open/solve transitions. Real inbound creation/reopening events run after control validation. Optional exact attribute-name filters limit attribute events. Unchanged values do not emit update events; typed boolean/number changes remain distinct.

Simulations, CSV imports and mutations produced by rule actions do not emit these contact events. Initial custom fields belong to the creation event rather than a second added event. Human-held conversations suppress event dispatch. First eligible rule per event follows priority and segment checks. Different event types from one source change can each run a rule; use final handoff to hold further automation when review is needed.

Recent execution history records rule/contact identifiers, trigger, outcome and bounded action metadata, without raw message text or previous attribute values. Missing dependencies and contact capacity are visible as blocked runs. REA recovered static trigger names in parent evidence ev_4376299527698ac5aebbb60e39a14fa2db97e8587f851a196004339625725f28; static names do not establish exact WATI runtime equivalence. No-response/call/social events remain pending.
