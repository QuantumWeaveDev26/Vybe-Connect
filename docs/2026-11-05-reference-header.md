# Reference header and smaller metric characters

User approved the page preview and requested smaller avatars, the supplied header, and no other page redesign.

## UI scope
- Full-width white header: VYBE branding, actual workspace picker, rounded search, WhatsApp setup link, actual mention-notification bell, profile dropdown.
- Search includes current workspace contacts, saved agents and real page destinations. Selecting an agent opens its Ask surface without running AI.
- Profile menu uses authenticated user data and existing profile/security/refresh/sign-out controls. No placeholder notifications or invented user photo.
- Four 3D character sprite positions from the approved page image. Desktop artwork82x108px, mobile62x81px. Existing metrics, captions and other page bodies remain unchanged.

## Artwork provenance
Built-in image-generation tool, no OpenAI API key or provider testing used. Rejected standalone characters were not added to the project.
Project asset: static/metric-characters-v2.png, exact copy of approved generated page preview exec-272be13f-7c6c-4b68-b213-c5c40ba4b83e.png. No raster edits; CSS selects four regions.
Prompt summary: use the approved original VYBE UI as style reference; render Campaign overview in warm white, mint and emerald; four equal real-zero metric cards with new stylized 3D toy-like characters: auburn ponytail contact organiser, glasses-wearing campaign announcer with megaphone, curly-haired headset message assistant, silver-haired consent guide with check shield. Preserve clear metric text, restrained depth and uncluttered navigation. Show a full-page desktop design preview, not standalone realistic portraits.

## Verification
22 JavaScript suites, all static JavaScript syntax checks and five HTTP/release tests passed. Fresh code review found and fixed the global-header/AI-drawer stacking conflict and stale-agent-chat revision handling; a regression check covers agent switching. Deployment readback passed: action123814359 succeeded, one healthy app container, source initializer exited0. /healthz and /readyz returned200, root200, authenticated state401 without a session, /.env404. The five changed public UI assets matched the pinned release by SHA256. Deployed Compose and environment exactly matched the candidate. Local browser control is disabled, so this release must not claim current physical-device or browser visual acceptance. Recovery-email delivery, credentials encryption, number reconnection and customer onboarding acceptance remain separate work.

## Deployment record
App release:5d46c6dd5f8efa392ec1e1acf9203c173d0c1755. Archive SHA256:ad582fe52b24118189606d89e7ab43364f3893c9b94416f18d359a2dc6497adf. Hostinger VPS1871828, existing vybe-connect project, action123814359. Only source initializer and pinned source paths changed; private environment and data volumes preserved.

The approved generated character sheet and reference header are used. Standalone realistic character images were rejected and never deployed. No paid provider acceptance tests were run.
