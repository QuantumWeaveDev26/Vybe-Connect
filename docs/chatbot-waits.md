# Persistent chatbot waits

The visual chatbot builder supports wait nodes with an integer duration from 1 second to 7 days. Sessions persist the due time and flow version in SQLite. A dedicated local timer continues one due conversation transactionally; concurrent workers cannot create duplicate continuation drafts. Chained waits begin from the actual continuation time, avoiding catch-up bursts after downtime.

Incoming messages during a wait are recorded without skipping the delay or supplying an answer to a question that has not been asked yet. The next question waits for a later inbound message. STOP, human takeover and saved flow settings cancel active sessions. Every flow save increases its version and cancels its existing question/wait sessions; existing runs do not preserve an immutable old graph snapshot. Disabled, missing or stale-version flows cannot continue.

The inbox shows the due time for active waits. Timer continuations produce the same unsent message drafts and local tag/status/handoff changes as the existing graph engine. They do not submit WhatsApp messages or call AI providers. Template-based live drip sequences remain a separate workflow.

This adds persistent timing to the independent graph runtime, not complete WATI automation parity. Live graph sending, integration and AI nodes, published versions, round-robin assignment, visual condition/operator parity and the full WATI node vocabulary remain incomplete. Local tests cover restart, time boundaries, competing workers, chained delays, early inbound messages, STOP, takeover, edits and disablement.
