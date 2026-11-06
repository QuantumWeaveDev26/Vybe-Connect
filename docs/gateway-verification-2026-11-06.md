# Original gateway adapter verification — 6 November 2026

## Scope and source

The added `ai_gateway.py` is original VYBE code. No Evolution API, New API or Routerly implementation source was copied. The existing ChatbotX MIT notices remain intact. A separately operated gateway still has its own licensing requirements; interoperability is not a license waiver.

## Verification

* Full Python suite: 672 tests, 671 passed and one Windows/POSIX-specific skip. No failures.
* Focused AI/gateway/connection/chat/customer-assistant/knowledge checks: 67 passed after correcting a database-handle cleanup issue discovered on Windows.
* All 28 JavaScript suites passed, including all 31 destinations, masked gateway credentials, opt-in usage, escaping and workspace-switch cleanup.
* Gateway tests exercised operator URL/model restrictions, default-paused configuration, private keys, Responses structured output, atomic quota reservation, unknown outcome accounting, tenant isolation, the real chat worker, and protected in-flight provider changes using isolated provider responses.
* Python compilation, JS syntax, Git whitespace and cache-version updates passed.
* REA connected to the user's Chrome endpoint at port 9223 and passively observed the WATI Team Inbox target. Its DOM inspection was policy-filtered and cannot establish full feature parity. No account changes or messages were sent.
* No paid inference, embeddings, messages, calls or payment tests ran. No synthetic production records or gateway endpoints were added.

## Limits

The gateway connector is deployed code, not an installed New API/Routerly service. `TW_AI_GATEWAYS` remains unset/empty in production; the connection button is hidden until an operator approves an actual endpoint and models. Live gateway compatibility, remote cancellation, automatic virtual-key provisioning and usage billing remain unverified/unimplemented. The daily request cap is not a currency spending cap. Meta's official transport and existing runtime gates remain unchanged; no QR transport was installed.

## Release

Runtime: `5301fac0cd8a9af01bb5d585863f8cbcd8d4446f`.
Archive SHA-256: `e6aa960187ce874eef4436271e6ce70413ea7a09b7d33602feb84331d426d9a5`, 4,943,456 bytes.
Hostinger action: `124014675` succeeded. App container healthy; source initializer exited zero. Runtime logs confirmed PDF/timezone and credential-vault probes without a traceback. All 45 deployed JS/CSS assets matched the runtime source byte for byte. Ten public HTTP checks passed, including health/readiness, protected state, private-source denial and invalid OAuth rejection. CSP present. Compose readback matched the candidate exactly and the private environment was unchanged. No gateway was activated.
