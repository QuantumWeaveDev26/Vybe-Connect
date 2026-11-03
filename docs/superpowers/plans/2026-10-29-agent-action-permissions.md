# Per-agent proposal permissions

Continue approved AI-agent implementation inline. Add administrator-selected allowed proposal actions to each background agent: tag, assign, note, draft_reply and task. Empty means informational findings only. Legacy agents default to all five existing review-first actions. No sending, billing or arbitrary tools are introduced.

Expose only selected proposals in the model contract and reject any disallowed response before publishing any findings. Store an incrementing agent configuration version in the context; if edited while generation is running, discard the late output. Recheck current permissions and archive state when an administrator approves an existing finding. Changes revoke pending proposals immediately without deleting history. Old findings resolve their source agent through the existing run record. Deleted or unavailable agents fail closed. Information-only acknowledgements and dismissal remain available.

- [x] Write failing configuration, generation-contract, stale-output and approval-revocation tests.
- [x] Implement shared permission vocabulary, agent versions and server checks.
- [x] Add editable action checkboxes, escaping and scope guards to agent setup.
- [x] Run regression checks and update documentation/package/local server.

Final local verification: 328 Python tests passed in 142.135 seconds, compilation and Node/UI checks passed. Server restarted and HTTP assets checked. Source package refreshed; provider usage and full WATI parity remain unverified.
