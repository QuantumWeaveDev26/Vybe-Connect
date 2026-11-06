# Gateway options reviewed on 6 November 2026

No source from these three projects has been incorporated or deployed in this release. They are separate services, not drop-in replacements for VYBE's tenant controls or provider verification.

## Evolution API

https://github.com/evolution-foundation/evolution-api

Supports both Baileys/WhatsApp Web sessions and the official Cloud API. QR linking is technically feasible, but the Baileys path is unofficial. It does not confer official WhatsApp Business Platform authorization or bypass its approval requirements. Session loss, upstream protocol changes and account restrictions make it unsuitable as VYBE's default transport for paying business customers. Keep the existing official Meta transport as the production path.

The current LICENSE is Apache 2.0 with additional conditions: retain frontend branding/copyright when using frontend components, and disclose Evolution usage to administrators in settings/documentation. It is not simply unmodified Apache 2.0. The stack also requires Node and a database, with Redis recommended.

## New API

https://github.com/QuantumNous/new-api

A possible separate AI gateway for routing, scoped access, quotas, usage logs and cost accounting. Of these options it best matches a future customer AI-credit/subscription offering. Keep gateway accounting separate from VYBE's authoritative customer subscriptions, and use per-workspace credentials and enforced budgets. Upstream model usage still costs money unless the selected provider/model is actually free or self-hosted.

License: AGPL-3.0. Retain notices and meet applicable corresponding-source obligations for modified network-served versions. Do not paste its code into VYBE and assume existing licensing remains unaffected. An independently deployed service is the preferred integration boundary; precise license obligations still depend on the actual combination and modifications.

## Routerly

https://github.com/Inebrio/Routerly (default branch develop)

A lighter alternative for model routing, fallback, budgets and cost controls. Core configuration uses JSON files rather than a database/Redis. This still needs an operated server and persistent storage; it is not zero infrastructure. Current README documents 11 routing policies, rather than the suggested nine. LLM/embedding-based routing itself can incur provider charges; cost-only routing avoids that extra model step.

License: AGPL-3.0, with commercial-license inquiries offered upstream. Use it as an alternative to New API initially, not an additional compulsory layer. Provider API compatibility, tenant enforcement, persistence and failure behavior require isolated adapter tests before activation.

## Recommendation

Retain official Meta Cloud API. Evaluate one AI gateway as a separately deployed, pinned service after the current feature release. Prefer New API when quota/accounting/subscription administration is the priority; prefer Routerly when a smaller routing/fallback layer is sufficient. No gateway can make paid upstream inference free, guarantee WhatsApp account safety or establish full WATI parity.

Sources: each repository's current README/LICENSE; WhatsApp's official guidance at https://faq.whatsapp.com/1217634902127718/ and https://faq.whatsapp.com/361005896189245/.
