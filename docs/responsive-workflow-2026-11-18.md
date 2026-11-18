# Workspace layout and setup workflow

Removed the customer-facing parity checklist route and the opening-animation replay button. Existing checklist documentation remains in the repository. Unknown legacy routes fall back to Campaigns.

Navigation starts collapsed unless the user has explicitly chosen otherwise. At normal laptop and tablet widths, section navigation becomes a horizontally scrollable tab row so it does not consume a second sidebar. Wide screens retain a section sidebar and a bounded content width. Mobile keeps the navigation drawer, stacked content and independently scrollable tables.

The developer page now links directly to WhatsApp and built-in AI. External agent endpoints and webhook integrations are optional, with no automatic token creation or fabricated connection. Both operator and customer subscription views use the same plan cards and provider checkout gates. Google setup displays its real platform dependency and offers existing CSV import as an alternative. Unchosen routing availability is explicit and links to the existing availability form; no availability was changed for any teammate.

## Verification

- 37 JavaScript suites passed, including setup workflow, all 30 routes, subscription gates, connector interactions and membership checks.
- 32 HTTP tests and 12 team-operation tests passed against isolated local stores.
- Browser checks covered all 30 routes, four sizes each (120 route/viewport checks), from 320 px phone width through 2560 px desktop width. No page-level horizontal overflow or missing heading was observed.
- Mobile drawer open/Escape close and optional integration disclosure were exercised. The reported 1191 px laptop layout was inspected with expanded navigation.
- Existing font warning from the design detector was retained to preserve the approved theme.

## External setup remains necessary

The production offline preflight reports platform AI and Meta onboarding configuration present, while subscription checkout and Google connections need setup. Razorpay activation, verified plan IDs and private keys; Google OAuth web-client credentials; and Meta Tech Provider approval cannot be replaced with a UI success badge. No paid prompts, messages, charges, provider activation or new integration credentials were submitted for this release. Browser viewport tests do not establish physical-device acceptance or live-provider acceptance.
