# Customer signup release

Application source `c794bfb` deployed to the existing VYBE Connect project using Hostinger action `123788054`. Actual container readback showed exactly one healthy application container and an initializer exited 0. Existing environment, data volume and proxy network were preserved. The platform application ID and WhatsApp configuration ID are configured privately; the existing app secret was reused server-side and a distinct callback verification secret was generated. No customer connection or sending was activated by this deployment.

Live HTTP readback: root, new signup script, privacy, deletion, health and readiness 200; unauthenticated application state 401; credential paths and `.env` 404. The root includes the signup asset and permits the explicit Meta SDK host in CSP. This proves deployment/HTTP configuration, not an actual SDK authorization or message delivery.

Full regression passed 575 Python tests with one POSIX-only permission skip, followed by 14 signup tests and 30 HTTP tests after final changes; all JavaScript checks including trusted-origin, repeated completion and stale-workspace isolation passed. Local browser access was disabled, so current rendered visual acceptance and live Meta signup remain unverified. No messages, calls, AI prompts or other paid test operations were sent.

The review draft still needs end-to-end recordings and its messaging API requirement. Customer account registration/migration/coexistence and encrypted application-level credential storage are not implemented by this increment. See `customer-whatsapp-onboarding.md` for exact behavior and limits.

## Button/retry repair

Source `112a5d0` deployed with action `123789238`. Signup preparation and cancelled/empty OAuth responses now explicitly redraw the connection UI; they no longer depend on the general refresh function detecting changed server data. Errors persist on the page and retry becomes available. Regression tests reproduce unchanged server snapshots, no-code responses and Meta cancellation, in addition to the existing trusted-origin/session-scope tests. All JavaScript checks passed. Live readback confirmed the repaired script, health/readiness 200 and exactly one healthy app container. The user observed a Meta popup opening and closing without a returned code; Meta JavaScript SDK domain/login configuration and actual OAuth acceptance remain unverified. No message or paid test was sent.
