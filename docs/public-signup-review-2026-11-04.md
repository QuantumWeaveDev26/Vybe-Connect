# Public registration and remembered sign-in

The operator explicitly requested a public business platform. VYBE Connect now has a separate Create account flow instead of treating initial-owner setup as customer registration. TW_PUBLIC_SIGNUP controls its availability and remains false by default for private installations. The live deployment enables it after the real platform owner is initialized.

Each new account receives a new business workspace and administrator rights only in that workspace. Public signup cannot initialize the platform, replace an existing account, select an existing workspace or gain platform-operator access. Passwords remain salted and hashed. Origin and bounded authentication-attempt checks cover the signup endpoint. The configured operator email is reserved across account-creation paths, with initial protected setup as the only exception.

Security review found an email-comparison mismatch: registration/login used lower(), while operator authorization used casefold(). All owner identity comparisons now use the existing lower() account semantics. Regression checks cover Unicode lookalikes and attempts to claim an unregistered reserved operator email through signup or member creation.

Keep me signed in requests a 30-day server-side session and matching Secure/HttpOnly/SameSite cookie. Unchecked retains the prior 12-hour lifetime. Only an explicit JSON true selects the longer lifetime. MFA remains required where enabled. Logout, password changes and security revocation invalidate remembered sessions. Passwords are never placed in localStorage. Existing sessions retain their original expiry; the option applies at the next sign-in or signup.

Public forms are concise, include Show/Hide password, and do not request a deployment token. The first-owner setup endpoint remains protected. Email ownership verification is not implemented or claimed; email password recovery remains unavailable after failed SMTP connectivity, and email work is paused as requested. Public registration does not activate WhatsApp, OpenAI, payments, subscriptions, calling or shipping for a new tenant.

Final regression: 535 Python tests passed in 273.233 seconds. The prior run had a three-second worker-event timeout; all 16 flow-sending tests and the fresh full suite subsequently passed without changing flow behavior. UI checks pass for all 21 routes, signup/sign-in state, field-local password visibility, connector events, directory behavior, service lifecycle and six map viewport geometries. Independent security review found no remaining actionable issue.

Live UI checks preceding this release confirmed the compact mobile navigation, full-width AI panel with no horizontal control overflow, a correctly contained Add Contact dialog, and working Show/Hide in the account-password form. No account password was entered or changed and no sample production records were created. Additional changes remove the duplicate mobile campaign context bar, suppress a help launcher that overlapped the AI composer, and prevent nested opening-screen scrollbars.

Provider transactions and full WATI parity remain separately unverified. Public signup and successful automated tests are not a paying-client production clearance.

## Live deployment evidence

Release `75505489f6af23373e6e01559fa3f47dca894487` deployed via Hostinger action `123642984`, archive SHA-256 `9ae699d7931540c02d1e662ee5090429cca9002c7fcce7b42157bb45828e2638`. TW_PUBLIC_SIGNUP=true is enabled in the private environment. Existing owner data volumes, scoped credentials and provider gates were preserved. The temporary SMTP-check service is absent from the current container list.

Health and readiness returned 200. Bootstrap reports initialized=true, signup_available=true and review_available=false. Invalid same-origin signup input returns 400 without creating an account; a cross-origin signup probe returns 403. Unauthenticated state remains 401 and `.env` remains 404. All 37 live assets match the release after normalizing Git line endings. The app container is healthy.

The real public Create account and Sign in views were inspected in-browser. The registration page shows business/name/email/password and a checked 30-day option, with no deployment token. Desktop and 390-pixel registration checks found no overflowing form controls. Show/Hide works in sign-in and the account-password form without entering/changing a real password. The refreshed owner workspace has no recorded browser-console errors. At mobile width the AI panel has no overflowing controls and the help launcher is hidden while it is open. Browser sizing was restored afterward. No production sample account or customer record was created during verification.
