# Launch check — 24 November 2026

## Repairs

- Replaced the page-splitting AI drawer with a focused native dialog, full-screen on phones. Ask, Agents, Knowledge, Activity and History remain available.
- Closing AI stays closed during refreshes and when an in-flight run finishes. Agents returns to the catalog rather than opening a second catalog inside the panel.
- Agent runs show a waiting state immediately. Request failures appear inside the AI window and leave the composer usable. The UI also respects the server's minimum monthly-budget reservation.
- The inbox uses the available screen height, with messages scrolling separately and reply controls visible. Contact details can be opened explicitly on all device sizes.
- Removed a sticky-navigation spacing conflict and prevented the help launcher from covering inbox actions. The existing mint/lilac/peach/sky theme is retained.

## Verification

- Unpaid isolated backend acceptance: 773 tests, 1 skipped, all executed tests passed; external network blocked.
- JavaScript checks: 44 suites passed, including intentional dialog opening, close persistence, run progress, error recovery and budget gating.
- Browser layout checks: all 30 application routes at 320, 390, 768, 1366 and 1920 CSS pixels, no horizontal document overflow. Closed-details descendants produced false positives in a preliminary control-name scan; their visible controls are named.
- Actual local browser saves: private note, template draft, campaign draft, custom agent, deal, follow-up task, automation rule and contact. The new-contact rule applied the expected tag and recorded a real local execution.
- Unconfigured WhatsApp submission and campaign launch remained blocked. No external messages, Meta submissions, charges, payment transactions or shipping operations were performed by these checks.
- All 12 agent presets had real OpenAI acceptance earlier on the same date, using synthetic data and the unchanged provider/prompt implementation. A fresh deployed Ask reply is checked separately in the release evidence; tests above are not claims of live provider delivery.

## Scope of teammate rollout

Internal CRM, platform-managed team AI within the approved monthly allowance, installable web-app access and manual WhatsApp handoff can be reviewed by invited teammates. Manual handoff does not synchronize WhatsApp history, messages or delivery states.

Automatic WhatsApp reception, sends, campaigns and customer auto-replies still require an eligible connected API number and provider acceptance. Customer Tech Provider onboarding remains subject to Meta review. Customer checkout needs activated Razorpay credentials and verified plans; Google connections need the platform OAuth client. Real recovery-mail delivery, audio calls, payment/shipping acceptance and installation on physical Android/iPhone devices are separate acceptance work.

This is an internal-team rollout check, not a claim that every provider-dependent feature or full WATI/Emovur parity is launch accepted. No successful result is fabricated for an unconfigured service.
