# 5 November 2026 UI repair release

Deployed source: a6925a33455b890ce355a0a12c0a2a9b5211a3a4.
Archive SHA-256: 41ce52cc77d699e59a00ded3321895b7c08a964018904c3d02138887871bb960.
Target: existing Hostinger VPS 1871828, project vybe-connect.

## Changes

- Replaced metric mockup crops with an artwork-only local transparent atlas; removed the old screenshot asset.
- Removed all legacy vector-person fallbacks. The agent catalog, template picker and Help use original 3D artwork. All twelve preset agents have distinct identities. Six new role-specific portraits and eight exclusive template portraits were generated after the user rejected reuse across sections. The template and specialist families do not reuse the metric-card or Help portraits. See docs/avatar-assets.md for the prompt set and files.
- Replaced the legacy topbar controls structurally, eliminating the duplicate mobile profile circle. Profile, mentions, search and refresh retain real actions.
- Added scoped inbox assignment, agent-team, tag, consent, reply-window, attention and sorting filters. An existing selected conversation and unsent draft are preserved when outside the new filter.
- Added per-file versioned script/style URLs and a release refresh utility, with Windows/Linux newline normalization. HTML and assets also retain no-store responses. An already-open tab must be reloaded once.
- Enabled existing configured recovery SMTP transport. One owner reset request was made; the generic HTTP response does not prove account eligibility or delivery. No arrival was found in the connected Gmail inbox during this release check. Real delivery remains unverified. No password was changed.

## Verification boundaries

24 JavaScript suites passed, including all 22 main routes, safe avatars, role gates, connectors, header actions, inbox filters, stale workspace protection and recovery UI. Nineteen recovery-focused Python tests and five asset/initializer checks passed. These local tests include mocked transports, not real AI, payments or call acceptance.

REA launched isolated headless Chrome against a temporary synthetic workspace, separate from production. Captures checked campaigns at 320 and 390 pixels, mobile Help, mobile inbox filters, the desktop template picker and all twelve expanded agent cards. These are browser viewport checks, not physical iOS/Android device acceptance. All twelve cards used 3D artwork. No production customer data, paid AI request, outgoing WhatsApp message, call, payment or shipping operation was used.

## Actual developer tools and remaining gaps

Connectors opens the developer console, integrations and webhooks. Existing webhook tools expose the Meta callback, signed agent event contract and delivery history. They are not WATI personal API-token management or a full general-purpose public API. Those remain to be implemented. The current analytics page has recorded message traffic, CSV export and current operator workload; WATI's advanced operator performance, calls, chatbot and CX reports are not fully built.

Credential encryption, number registration/reconnection gaps, complete onboarding acceptance, calling/commerce provider acceptance and broader feature parity remain separate unfinished work. Meta approval cannot be completed by UI code. Paid live-provider acceptance was deliberately not run under the user's no-spend restriction. Website legal-provider changes remain deferred at the user's request.

Private environment and persistent volumes were preserved. Only TW_RECOVERY_ENABLED changed from false to true in this work. Production credentials and customer records were not added to Git. Initializer pins are recorded in deploy/hostinger_source_init.py.

Deployment action 123826702 succeeded. Exactly one app container is healthy and source initialization exited zero. All 41 versioned JavaScript/CSS files matched committed release bytes and URL hashes; the two new WebP atlases and clean metric PNG matched the release bytes and correct image MIME. Health/readiness returned 200, anonymous state 401, private .env 404 and removed screenshot artwork 404. Private configuration readback matched the deployed candidate. Mobile template-picker framing was additionally checked at 390x844.
