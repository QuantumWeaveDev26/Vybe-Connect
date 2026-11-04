# Overall UI review

User steering: prioritize the whole platform, concise text, usable controls and real service behavior. Pause SMTP investigation and remove its temporary checker from the private deployment configuration. Keep SMTP disabled after failed connection checks; no email has been sent.

Browser access became available. The authenticated desktop screens were inspected, and mobile Campaigns showed a severe context-navigation shrink: the duplicate Create New Campaign control became a vertical column of letters. Fix that observed issue, keep tab labels intact, and remove redundant helper prose. Retain the centered world-map implementation.

- [ ] Fix compact context navigation and concise campaign/analytics copy; retain detailed report semantics in a collapsed disclosure.
- [ ] Add explicit Show/Hide controls to shared password fields, including account changes, invitations and reset forms. Never change the account password or weaken MFA.
- [ ] Check live forms/screens without saving sample production records or invoking chargeable operations. Use isolated tests for persistence and contracts.
- [ ] Run affected tests and review changes, then pin and deploy the new release while preserving private token/environment and data volumes.
- [ ] Verify live mobile/desktop layouts, password controls, navigation, assets and health. Report provider acceptance gaps separately.
