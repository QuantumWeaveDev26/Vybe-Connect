# Sign-in and connector review, 4 November 2026

## Changes

The account-entry form now supports password-manager autofill, a Show/Hide password control and a Caps Lock hint. Authenticator/recovery-code inputs are collapsed initially and open automatically when the server rejects a missing or incorrect second factor after password validation. Errors and busy states are clearer. Responses arriving after the form has been replaced cannot rerender another view or change the current workspace selection. Authentication, password hashing, MFA and session rules are unchanged; no account password was reset.

The green sign-in presentation has more room for inputs and wraps at narrow widths. The connector icon opens an accessible click/keyboard/hover navigation popover linking to API, Integrations and Webhooks. Clicking pins a hover-opened menu; Escape, outside click, scrolling and navigation dismiss it. The developer console has a checklist based on real saved settings and event state. The new Webhooks route displays the current callback and real delivery history. API contract documentation remains available. No unsupported API-key generator or simulated success state was added.

The centered opening-map implementation from release 07ce224 is retained and its six-viewport containment/centering tests pass.

## Verification

522 Python tests passed in 306.612 seconds. JavaScript checks cover sign-in controls, MFA expansion, stale forms, connector destinations, menu interaction sequences, all 21 routes, directory filtering, service/microphone lifecycle, renderer privacy, and map geometry. Independent review identified the first-click/hover interaction bug; it was reproduced in a failing test, fixed, and passed re-review.

Browser control remains disabled by Work settings. Actual browser rendering, hover appearance and physical-device responsiveness are not visually verified. Source and lifecycle checks do not establish pixel-perfect WATI parity.

## Private configuration and service boundaries

After an environment-form save removed the long Meta token, the complete token was restored as an app-service environment override in the private Hostinger Compose configuration (action 123624993). It is not in the repository and does not use the form's 256-character field. Preserve that private Compose override in later edits/deployments.

Read-only Meta checks accepted the phone number and App Secret proof, WABA template access and webhook verification. However, the saved WABA's three-number inventory did not contain the configured Phone Number ID, nor the same displayed phone number. The owner was asked to supply both IDs from the same Meta API Setup number selection. Their individual accessibility is not confirmation that they belong together. OpenAI model metadata access passed; no paid inference was run. Razorpay/Shiprocket credentials remain absent; calling, paid transactions and live delivery were not exercised.

The owner selected Gmail for password recovery. A protected configuration file was opened outside the repository. At review time its password did not match the Google App Password format, so no SMTP login or email was attempted and recovery remained disabled. An actual App Password and subsequent server-side mail/delivery verification are required. No Gmail secret is included here.
