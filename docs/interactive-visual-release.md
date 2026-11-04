# Interactive visual release

Reference review: all 18.70 seconds of the supplied video sampled at 0,1,2,3,5,6,8,10,12,15 seconds, plus user-supplied screenshots. Observed pale lavender background, dotted logo, delayed dotted world reveal, cursor displacement and purple transitions. Original WATI Astra page inspected read-only through REA on November 4, evidence ev_2321fbeec6d8b64d894a5d23e3a0e9675177edc1bce1d475488db8d749933e66 and screenshot ev_7b93f69b83f9a3bf9757e94d47026e13103b7744525e46033d7af3313a95df34.

Implementation: 5,247 Natural Earth land dots, spring-based local cursor displacement, original dotted V mark, purple motion, smooth dismissal, explicit entry and replay. Reduced-motion skips continuous animation; teardown cancels frame work and event listeners. No cursor coordinates leave the device. Automatic entry is about 4.2 seconds after render, extended during pointer activity up to a 12-second ceiling. Replay is available in the rail.

Navigation has compact monochrome icons, short black hover/focus labels, active states and explicit expansion. Astra cards use original SVG character avatars. The template picker has eight instruction starters, category filtering, text search, selection and handoff to the real customer-assistant form. It does not create a live calendar, automatic enrollment or payment capability. Existing assistant settings are presented for review; templates force disabled draft mode until explicitly saved. Help home cards route to real AI, guided tours, Astra and workspace feedback.

Land data: Natural Earth ne_110m_land, public domain. Source: https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_land.geojson . Dots generated offline, no third-party asset request at runtime. Avatar artwork is original vector code, not WATI or Bitmoji assets.

Functional and exact visual parity with all of WATI remains unverified. No provider activity or account changes on WATI were performed.

Validation: JavaScript renderer/navigation/privacy checks, template filter regression and avatar input safety passed. Five public-review Python tests passed. Browser verified all 13 rail icons, short Team Inbox focus label, healthcare filter selecting the correct appointment form with enable unchecked, fixed template footer, help panel and a 375px content width without horizontal overflow. No paid providers were invoked.

Deployment: application 1f3827f058a4b333c43e2a58902d683c52340f15, Hostinger action 123589900 succeeded. Initializer exited 0 and app healthy. HTTPS healthz/readyz returned 200; all 34 served frontend/data assets matched source. Live browser verified eight template choices, correct healthcare prefill, disabled replies, help home and cursor displacement on the world map, with no console errors. Screenshots are retained outside the source checkout in outputs/release-evidence.
