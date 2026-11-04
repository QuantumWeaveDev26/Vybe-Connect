# Transition from public preview to real owner access

The operator supplied an owner email privately in the session. TW_PLATFORM_OWNER_EMAIL is configured only in the private deployment environment. Initial owner setup is now bound to that email as well as the existing private deployment token. The allowed email is not exposed by bootstrap. The owner chooses the password in the live form; no password is generated, committed or sent in chat.

TW_PUBLIC_REVIEW=false closes public sample access. Existing application data, owner setup token and other provider gates are preserved. The production database is not replaced by the sample store. Provider activation remains off until credentials and approved acceptance tests exist. Removing the preview does not mark incomplete calling, onboarding or provider behavior complete.

Verification: production setup rejects a different owner email without creating an account, does not disclose the configured email in bootstrap and accepts the correct email only with the existing token. Further owner creation and provider acceptance are separately tracked; a prepared form is not a completed account.

Full regression: 518 Python tests passed in 267.512 seconds, plus JavaScript renderer/navigation/privacy checks. This verifies the code changes, not provider acceptance or completion of the owner form.
