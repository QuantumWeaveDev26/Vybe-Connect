# Background agent action controls

Each background agent has an administrator-selected set of permitted proposals: add a tag, assign a teammate, add an internal note, create an unsent draft or create a follow-up task. Selecting none produces information-only findings. Existing agents retain their previous five-action vocabulary until edited. New agents and AI-proposed installations use that existing default; administrators can narrow it in Edit agent.

The server builds the analysis contract from the agent's permitted actions. Structured model responses containing a disallowed action fail the complete run before any finding is published. This is checked independently of instructions in the model prompt. Runs still only propose actions; administrator review remains mandatory.

Every saved agent configuration increments its version. Results from a generation started with a previous version are recorded as interrupted and discarded. Scheduling and archive controls retain their existing execution leases. Editing does not cancel a provider request already in flight or recover provider cost.

Approval resolves the originating agent through the saved run, checks that it still exists, remains active and still permits the proposed action, then performs the existing current-conversation fingerprint and age checks. A revoked or archived proposal cannot be applied. It can still be dismissed. Information-only findings can still be acknowledged. Restoring a permitted action can make an otherwise valid pending finding eligible again; no action is automatically applied.

These are action controls for the existing review workflow, not restrictions on which workspace facts an administrator-owned agent can read. They do not permit message sending, billing, deletion, arbitrary code or third-party API actions. Tenant roles and knowledge/provider gates remain separate. Exact WATI permission screens and runtime behavior remain unverified.
