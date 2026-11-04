# VYBE green and responsive cleanup

Fixed the missing sr-only utility that exposed accessibility labels as visible toolbar text. Search/status/count/new-agent now form a bounded desktop row and a two-row mobile grid. Agent titles, status, metadata and actions have dedicated rows. Preview notice is shorter, cards have stable widths, feedback stays available on demand instead of covering content, rail icons have compact height-dependent spacing, and focused controls use green.

The opening now uses green/mint rather than purple. World dots have stronger contrast, a full-width fitted silhouette, darker geographic labels and quieter contrast immediately behind the brand text. Cursor displacement, entry/replay, teardown and reduced motion remain intact. No cursor data is transmitted.

Validation: JavaScript renderer/navigation/privacy checks, template filter regression, avatar input safety and invitation/audio cleanup checks passed. Five public-review Python tests passed. Browser checks at 375px content width covered Inbox, Campaigns, Templates, Contacts, Flows, Pipeline, Commerce, Services, Analytics and Settings: no document-level horizontal overflow and no console errors. These are rendering/interaction checks, not live delivery/payment/shipment/audio acceptance.

Configuration: ENVIRONMENT_SETUP.md provides the exact code-backed names, provider webhooks, workspace-ID distinction, separate activation gates and remaining acceptance steps. .env.production.example now also contains Meta, OpenAI and optional connector names from .env.example. Official OpenAI model catalog consulted: https://developers.openai.com/api/docs/models/all . No paid calls or live flags were enabled.
