# VYBE green and responsive cleanup

Fixed the missing sr-only utility that exposed accessibility labels as visible toolbar text. Search/status/count/new-agent now form a bounded desktop row and a two-row mobile grid. Agent titles, status, metadata and actions have dedicated rows. Preview notice is shorter, cards have stable widths, feedback stays available on demand instead of covering content, rail icons have compact height-dependent spacing, and focused controls use green.

The opening now uses green/mint rather than purple. World dots have stronger contrast, a full-width fitted silhouette, darker geographic labels and quieter contrast immediately behind the brand text. Cursor displacement, entry/replay, teardown and reduced motion remain intact. No cursor data is transmitted.

Validation: JavaScript renderer/navigation/privacy checks, template filter regression, avatar input safety and invitation/audio cleanup checks passed. Five public-review Python tests passed. Browser checks at 375px content width covered Inbox, Campaigns, Templates, Contacts, Flows, Pipeline, Commerce, Services, Analytics and Settings: no document-level horizontal overflow and no console errors. These are rendering/interaction checks, not live delivery/payment/shipment/audio acceptance.

Configuration: ENVIRONMENT_SETUP.md provides the exact code-backed names, provider webhooks, workspace-ID distinction, separate activation gates and remaining acceptance steps. .env.production.example now also contains Meta, OpenAI and optional connector names from .env.example. Official OpenAI model catalog consulted: https://developers.openai.com/api/docs/models/all . No paid calls or live flags were enabled.

Deployed application e1f15d3363f045c48a1e513b1f3634a6dc1ac934 via Hostinger action 123602737. Initializer exited 0; app healthy. HTTPS healthz/readyz returned 200. All 34 frontend/data assets matched source. Live browser confirmed the shorter preview, clean agent card, no automatic survey, green world reveal and 375px mobile layout without overflow. No console errors appeared. Existing private environment and data volumes were preserved.
