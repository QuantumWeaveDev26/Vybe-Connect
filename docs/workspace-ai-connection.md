# Customer AI setup

Workspace administrators can save their own OpenAI project API key and model in Settings. Saving is paused by default; enabling real AI usage requires a separate, unchecked-by-default checkbox disclosing provider charges and enabled schedules. No provider request is made by saving, pausing or removing credentials. The global platform AI switch still applies. Existing operator environment configuration remains supported.

Keys are stored in private `TW_DATA_DIR/ai-credentials` files (0700 directory, 0600 files on Linux), isolated by exact workspace ID. They are never returned by application state, embedded in source, written to entity/audit data or provided as sample/default keys. They are not encrypted by the application; encrypted host storage/backups and restricted server access remain operational requirements. Disconnect writes a tombstone so an environment key is not silently substituted. Removal does not revoke the key at OpenAI.

Admin role and live session are rechecked before writes. Connection requests are origin-protected and rate-limited. The modal masks input, clears keys after submission and closes on workspace/session changes. Changing/removing a key is blocked while known OpenAI background work still needs it for reconciliation or cancellation; pausing leaves the key available to stop existing work. Already running provider work may continue until cancellation is confirmed.

AI state reflects configured credentials and gates, not proof of a real model response. Provider metadata checks remain a separate existing Services operation. No paid test prompt, message or call was sent. Full regression ran 587 Python tests successfully (586 passed, one POSIX-only skip); focused credential tests, new HTTP authentication/origin/privacy tests, and JavaScript UI isolation/default-spend/masked-input/cleanup checks passed after final changes.

Reference: https://developers.openai.com/api/docs/guides/api-keys

The confirmed legal-provider website correction was explicitly deferred by the user and is not part of this release. Meta Tech Provider verification is in review based on the user's screenshot; it is not approved by the website code.
