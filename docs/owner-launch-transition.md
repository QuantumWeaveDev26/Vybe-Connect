# Transition from public preview to real owner access

The operator supplied an owner email privately in the session. TW_PLATFORM_OWNER_EMAIL is configured only in the private deployment environment. Initial owner setup is now bound to that email as well as the existing private deployment token. The allowed email is not exposed by bootstrap. The owner chooses the password in the live form; no password is generated, committed or sent in chat.

TW_PUBLIC_REVIEW=false closes public sample access. Existing application data, owner setup token and other provider gates are preserved. The production database is not replaced by the sample store. Provider activation remains off until credentials and approved acceptance tests exist. Removing the preview does not mark incomplete calling, onboarding or provider behavior complete.

Verification: production setup rejects a different owner email without creating an account, does not disclose the configured email in bootstrap and accepts the correct email only with the existing token. Further owner creation and provider acceptance are separately tracked; a prepared form is not a completed account.

Full regression: 518 Python tests passed in 267.512 seconds, plus JavaScript renderer/navigation/privacy checks. This verifies the code changes, not provider acceptance or completion of the owner form.

Deployed application 5a48994ab74059fec2723203cd4f584e0a60e9ea via Hostinger action 123606802. HTTPS healthz/readyz returned 200; bootstrap reported review_available=false and setup_token_required=true; the former preview state route returned 404 and unauthenticated real state returned 401. Owner setup was prepared in the browser without entering a password or submitting it. Account creation remains user-controlled and pending confirmation. No provider credentials or activation flags were added.
