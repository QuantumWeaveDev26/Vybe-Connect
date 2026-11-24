# Internal team and customer subscriptions

Only exact workspace IDs in the private `TW_INTERNAL_WORKSPACES` comma-separated allowlist receive subscription-free CRM access. The production selection for this release is QuantumWeave AI (`eaa91c5fe6f20007`). Team members still need invitations/current membership and retain their existing roles and capability permissions. A browser flag, account name, email suffix, newly created workspace or customer payload cannot grant internal status. Invalid wildcard or malformed allowlists fail closed.

Internal access is not a fabricated paid subscription. Public service state distinguishes `internal_use`, `crm_access` and verified `subscription_active`. Internal workspaces cannot enter subscription checkout. External customers retain the existing configured-plan, provider-identity and active-period requirements.

Free internal app access does not approve provider charges. In platform-managed mode, internal AI is paused unless the operator separately sets `TW_INTERNAL_AI_ENABLED=true`. `TW_INTERNAL_AI_REQUESTS_PER_MONTH` must be 1–1000 (default 50); it is reserved atomically per UTC calendar month. The old per-workspace paid-call flag cannot bypass this internal gate. This release does not enable that gate, send prompts or messages, or change Meta/provider activation.

The existing services and AI settings show a concise internal-team summary, without subscription purchase prompts. Customer billing cards stay unchanged. The web application retains its existing CRM, sales, contacts, inbox, automation, knowledge, analytics and integration routes; this release does not claim full HubSpot/Odoo/WATI feature equivalence.

Mobile navigation synchronizes menu state across controls, focuses the drawer, traps Tab within it, supports Escape/close/backdrop dismissal, restores focus, and makes background content inert. The drawer includes a visible close control and independently scrollable destinations. Header touch targets are 44 px and workspace inputs avoid mobile focus zoom. Existing tablet/desktop section-navigation patterns and theme remain.

Verification is recorded separately: unpaid backend/renderer tests plus browser viewport and interaction checks. Physical device and paid-provider acceptance are not inferred from these tests. Keep the production credential/data mounts unchanged.
