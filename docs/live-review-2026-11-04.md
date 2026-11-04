# Live review: 4 November 2026

## Repairs

- The server's reusable-reply collection was incorrectly named `replys`, while every client workflow expected `replies`. Corrected the state contract; Reply Material and inbox reply selection can use the saved collection. Regression checks cover persistence and workspace isolation.
- The opening map now centers its visible land bounds and fits both width and height. Map particles and city markers share a transform. Coordinate labels are omitted on narrow screens and clamped on larger screens. Pointer interaction and reduced-motion behavior remain.
- Buttons and long headings wrap; intrinsic grid widths no longer force cards beyond their containers. Mobile workspace/AI controls occupy separate header rows with profile and refresh still accessible. Short landscape screens use a smaller logo and a scrollable opening surface.
- Settings distinguishes missing Meta values from invalid formats. IDs, App Secret and Graph API version are checked without exposing their values. Configured means required values are present with expected formats, not provider acceptance.

## Runtime evidence

The existing HTTPS webhook returned HTTP 200 with the exact verification challenge using the saved verify token. A read-only Meta lookup accepted the privately supplied access token for the configured Phone Number ID. A read-only OpenAI model lookup confirmed access to the configured model. These checks did not send messages, generate AI output, place calls, create shipments or charge customers.

Saved version initially contained an API URL; its version component is used for the correction. An initially invalid App Secret was subsequently corrected in the private Hostinger environment. Values and tokens are deliberately absent from this report.

A separate read-only template lookup against the configured WABA ID failed with Meta error 100, `Tried accessing nonexisting field (message_templates)`. The owner was asked to correct the WhatsApp Business Account ID privately. Successful phone metadata access does not establish WABA/template access. Razorpay and Shiprocket credentials are absent from the inspected environment, so their live connections were not checked.

## Verification boundary

Tests use isolated temporary workspaces and mocked provider contracts. All 20 main routes render from an actual isolated Store state. Six viewport geometry tests cover map containment and centering. These are not real-browser layout screenshots.

Final local regression: 522 Python tests passed in 236.346 seconds. JavaScript renderer/privacy, all-route rendering, directory filtering, service lifecycle and map geometry checks passed. Python compilation and JavaScript syntax checks passed. Independent source review reported no actionable findings.

Browser control reports `Local browser use is disabled in Work settings`. Actual hover appearance, pixel alignment, touch devices, microphone/calling behavior and authenticated production interactions remain unverified in this review. No alternative browser automation was used to bypass that restriction.

## Deployment verification

Application release `07ce22445d47ed043af6ba66c7c362a04f3270f5`, archive SHA-256 `58f74a10367655cec8a7cfa37f317720d30bdd9dd74cd5fdfeb8294d3a30a9d9`, deployed successfully through Hostinger action `123624292`. The existing environment and volumes were preserved. The complete privately supplied access token was added through the project API, and the version was corrected to `v25.0`. No provider activation flag was changed.

After deployment, health and readiness returned HTTP 200, the application container was healthy, and all 34 script/style assets matched the local release after normalizing Git line endings. The new map-layout module is served and loaded. Bootstrap still reports an initialized real owner and no public review access. Unauthenticated state returns 401; the public review route and `.env` return 404. The saved webhook token returned the exact requested challenge with HTTP 200. A Meta phone metadata request including an App Secret proof also returned 200 with the matching configured Phone Number ID. WABA/template access remains a separate unresolved configuration check.

Full WATI parity is not established. Razorpay/Shiprocket live acceptance, paid AI inference, real messaging delivery, calling acceptance, and production operational readiness require their separate approval and verification. Provider activation gates remain unchanged.
