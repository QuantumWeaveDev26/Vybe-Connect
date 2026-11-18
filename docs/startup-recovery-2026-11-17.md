# Loading-screen recovery â€” 17 November 2026

The user reported a page stuck at "Opening your workspace". At inspection, live root, health and bootstrap requests returned 200; anonymous state returned the expected 401. All 45 then-deployed JS/CSS assets matched the pinned GitHub release and scripts passed syntax checks. These checks establish server availability, not successful rendering in the affected authenticated browser. Browser access became unavailable during diagnosis, so the original browser-specific cause remains unconfirmed.

Two startup failure modes were reproduced with unpaid regression tests: a stalled request never finishes when abort timeout support is absent/ineffective, and a late state response can render after its startup request has expired.

The fix adds an independent Promise deadline with optional request abort, rejects late state responses before updating the workspace, and loads a small independent startup guard before application scripts. If initialization remains stalled after 30 seconds, it replaces the spinner with a reload control. The guard leaves a loaded workspace or sign-in form alone and does not clear cookies, credentials, drafts or database records. Existing retry/sign-in behavior remains covered by `tests/workspace_startup.js`; deadline, late-response and fallback behavior are covered by `tests/startup_deadline.js`.

The new script has a versioned URL and explicit static-server mapping. The modified application bundle receives a new content fingerprint. Live browser confirmation and deployment must be recorded separately; source tests alone do not establish that the reported incident is resolved in production.

## Chrome evidence and follow-up

The affected Chrome console was subsequently inspected through Windows Computer Use: 21 script requests had returned HTTP 502, including account, assistant, shell and service scripts. The remaining application script then stopped before boot at `clearSecurityDialog is not defined`. A later read-only burst of all 45 live CSS/JS requests returned 200. The original upstream cause of those transient 502 responses was not established. The independent recovery guard covers partial script loading; it is not a claim that provider or hosting outages cannot occur.

A separate reproduced compatibility issue is also fixed: denied or unavailable browser storage no longer aborts global initialization. Workspace/navigation/feedback preferences use an in-memory fallback; the native storage API is unchanged. No authentication tokens are placed in this fallback.

The existing customer billing page now shows Starter, Growth and Scale preview cards at INR 499/999/1499 monthly with 50/150/300 included AI requests. Real configured plans replace the previews. Preview/unconfigured checkout and repeat purchases for active subscriptions remain disabled; no Razorpay plan IDs, payments or subscriptions are fabricated.
