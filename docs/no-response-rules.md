# Customer no-response rules

Administrators can select **Customer has not replied** in Automation rules, set a wait of 1–604,800 whole seconds and choose existing local actions. Rules can create unsent drafts or internal tasks, update tags and text attributes, assign members, change status or hand off to a human. They never send externally.

A watch begins when the provider accepts a new outbound text, template, customer AI reply or supported media message. Drafts, simulations, failed and uncertain sends do not start watches. Delivery/read updates do not reset the timer. The latest accepted reply replaces the preceding watch.

Creating or saving a rule establishes a message-ordinal watermark. Messages already created before that save are excluded, including pending messages accepted later. This avoids historical replay. Each rule independently evaluates once per eligible accepted reply, against the current contact segment and available dependencies. Non-matching or blocked evaluations are recorded and do not automatically retry.

A later real inbound prevents evaluation regardless of the sender's timestamp. Synthetic inbound does not cancel a real watch. STOP, staff takeover, rule/AI/graph human handoff and received non-text attachments remove watches. Resume does not restore them. Replies accepted while automation is held do not arm watches.

Due evaluation uses one SQLite transaction with a unique workspace/rule/message identity. Concurrent workers cannot apply the same evaluation twice. The local one-second worker survives restarts; actual scheduling can run later if the server is offline or busy. Latest 100 evaluation records and rule execution results appear in the interface. No calendar/business-hours scheduling, repeated unattended follow-up sends, or immutable rule versions are provided.

REA's captured WATI rules exposed a customer-no-response event name; this is an independent implementation. Exact WATI timing and internal protocol equivalence are unverified. Verification uses temporary databases and mocked transports; no provider usage is required.
