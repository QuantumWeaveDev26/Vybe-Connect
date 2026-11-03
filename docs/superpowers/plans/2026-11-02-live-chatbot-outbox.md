# Live chatbot text outbox

Implement the missing live graph transport inline while preserving full WATI scope. Default graphs remain draft-only. Administrators can configure live delivery before credentials; actual sending additionally requires configured/live Meta, a workspace FLOW_SEND server gate, current admin ownership and a real 24-hour customer service window. Simulation never sends.

Live interpretation stops at each message/question node and queues one durable text job. Only accepted submission advances the graph. Questions become answerable after acceptance; waits start from actual acceptance. Each job is claimed transactionally once with contact/session/flow-version/inbound-ordinal fencing. STOP, takeover, edits, newer inbound, missing membership and closed windows suppress queued work. Unknown or interrupted submissions are never retried automatically and require human review. Requests already in flight cannot be recalled. Record real provider statuses in inbox messages and expose bounded job history; acceptance is not delivery.

- [x] Add failing acceptance, ordering, question, delayed wait, gate, simulation, cancellation, unknown and competing worker tests.
- [x] Implement live interpreter checkpoints and guarded durable outbox worker.
- [x] Add flow delivery controls, runtime instructions and status history.
- [x] Verify, document provider limits, package and restart without enabling live gates.

Verified: 352 tests passed in 136.564 seconds, Node renderer and syntax/compilation checks passed, loopback HTTP assets checked after restart. Source ZIP excludes data/secrets/captures. Live gates remain false. Full WATI scope remains active and incomplete.
