# AI team-pool handoff routing

Continue the approved WATI-equivalent implementation inline. Existing routing preserves an active conversation assignee, otherwise uses one configured teammate and finally the assistant administrator. Add an optional least-busy routing mode over an administrator-selected pool of up to 50 current workspace members. Count assigned open/pending conversations from this workspace, excluding the conversation being routed; solved chats do not count. Break ties in configured pool order. Preserve an existing active assignee even outside the pool. Removed members are ignored at execution and an empty surviving pool falls back to the assistant administrator.

Routing runs inside the existing handoff write transaction, so concurrent handoffs see prior assignments. Record the chosen strategy and workload at assignment time in handoff metadata. No online-presence claims, capacity limits, notifications or external calls. Fixed mode remains the default. Settings edits use existing version cancellation. UI includes mode selection, member pool and routing summary. Keys remain last; use only temporary databases and mocked AI/provider transports.

- [x] Write failing workload, tenant scope, tie, removed member, assignment preservation and concurrency tests.
- [x] Implement validated settings and transactional member selection.
- [x] Add team-pool controls and documented routing history semantics.
- [x] Verify local checks, refresh the source ZIP and restart the local server.

Final local verification: 328 Python tests passed in 142.135 seconds, compilation and Node/UI checks passed. Server restarted and HTTP assets checked. Source package refreshed; provider usage and full WATI parity remain unverified.
