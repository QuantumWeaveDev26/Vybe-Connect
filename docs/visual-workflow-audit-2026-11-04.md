# Visual identity and workflow audit — 2026-11-04

## Changes
- Distinct original portraits for all 12 agent presets and 8 customer templates, with varied hairstyles, accessories and clothing. Custom names remain stable and are never interpolated into SVG.
- Separate Findings, Security, Password and Webhooks icons.
- Payment/shipping connection badges visible before the first order. Corrected unconditional disconnected-payment copy on the orders page.

## Verification
- 536 Python tests passed in 262.855 seconds using isolated test data and mocked provider contracts where applicable.
- All 12 JavaScript test files passed, including all 21 main routes, agent preset selection, auth controls, map geometry, connector interaction, media cleanup, unique portraits and provider state badges.
- Authenticated live browser: commerce navigation, fulfilment tab, AI Agents and Inbox Triage setup dialog opened. Dialog cancelled without creating an agent or invoking providers. Existing saved agent preserved.
- REA discovered the logged-in WATI Team Inbox at port 9223. Discovery alone does not establish feature or visual parity.

## Boundaries
No outbound messages, AI generation, charges, shipments or provider activation were performed. Passing local tests does not establish live delivery, payment acceptance, call audio or full WATI parity. AI was visibly disabled in the live workspace. Live release readback and visual review follow deployment.
