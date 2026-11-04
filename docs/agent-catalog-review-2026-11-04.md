# Agent catalog clarity review

The user supplied a screenshot of a dense suggested-agent list and asked for an easier, illustrated interface. Previously the list exposed the complete execution prompt on every card. The catalog now separates concise task descriptions from backend instructions.

Suggested cards use the existing original SVG portrait characters, a task category, one-line summary and Set up agent. Six presets are shown initially; Show all exposes all 12. Categories retain original preset indices. All 12 names and execution instructions match the previously deployed source exactly. No image-generation service or external avatar request is used.

Saved agent cards show a portrait, state and short task summary with Ask, Run now and Activity. Detailed instructions, schedules and configuration controls are inside Manage. Run now remains disabled when the runtime is not ready. Prefilled setup instructions and permissions are in a disclosure; blank custom instructions remain open. Role checks and backend execution/review gates are unchanged.

88 targeted Python tests passed: 29 agent tests (including a new contract exercising every actual preset), five AI tests, eight finding/review tests, six OpenAI adapter tests, three background-provider tests, 15 chat-job tests and 22 customer-assistant tests. The full-preset contract saved all 12, propagated their original instructions into mocked model calls, recorded completion, verified foreign-workspace rejection and asserted no sent messages, queue jobs or findings were fabricated. These are isolated contract checks, not live model acceptance.

JavaScript catalog, directory, renderer/privacy and all-21-route checks passed. Catalog tests cover avatars, concise copy, six/all-12 visibility, category indices, role controls and escaped saved instructions. Independent code review found no actionable issue.

The deployment was inspected with TW_AI_ENABLED=false and the owner's paid-call flag false. No paid inference, production agents, messages or automatic schedules were created. Browser control currently reports Local browser use is disabled in Work settings, so the new catalog's actual appearance and responsive layout remain visually unverified in this pass. CSS includes two-column cards, a single-column narrow layout, wrapping titles and reduced-motion handling.

This is a usability repair, not full WATI parity or production-service clearance. Outbound calling and other previously documented gaps remain; real OpenAI agent quality and provider transactions require separate approved acceptance checks.
