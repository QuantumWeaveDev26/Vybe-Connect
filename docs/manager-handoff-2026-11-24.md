# Manager handoff — 24 November 2026

VYBE Connect can be reviewed as an internal CRM with team AI and manual WhatsApp handoff. The QuantumWeave AI workspace has subscription-free internal access. External customer workspaces retain their subscription requirements.

## Use today

1. Open https://vybe.srv1871828.hstgr.cloud/ and sign in using your own invited account. Administrators can create a one-time invitation in Team management; share that link privately instead of sharing an owner password.
2. Open the account menu and choose **Install VYBE Connect**. Android Chrome and desktop Chrome/Edge offer browser installation; iPhone Safari uses Share → Add to Home Screen. The installed application still requires internet for CRM, messaging and AI. Physical-device installation acceptance remains separate from manifest/browser tests.
3. Add or import contacts, organise tags, save private notes, assign teammates, and manage deals and follow-up tasks.
4. Choose **Open in WhatsApp** on a contact. This opens the WhatsApp account already available on that device. The user chooses whether to send. It does not connect a central business number or transfer WhatsApp chat history to VYBE.
5. In a conversation without a connected API number, write an unsent draft and choose **Open in WhatsApp** to carry the text across. **Add note** stores a private CRM note; it is not a WhatsApp send. Manual WhatsApp messages and delivery status are not automatically recorded in the shared inbox, analytics or AI context.
6. Use the existing AI agents and approved business knowledge. Team OpenAI requests retain the operator-approved INR 299/month conservative shared guard. Installing the app and opening manual WhatsApp links do not enable new paid providers.

## Remaining external setup and acceptance

- Connect an eligible business API number and validate signed inbound events, actual outgoing delivery and reconnect behaviour. A regular WhatsApp phone account is not silently migrated or replaced. Tech Provider approval/customer onboarding remains separate.
- Configure Razorpay credentials and verified subscription plans before opening paid customer checkout. Google connections require the platform OAuth client.
- Verify real recovery mailbox delivery, calling/audio, payment/shipping provider operations and physical Android/iPhone behaviour before claiming those services are production accepted.
- Push the committed release to GitHub after authentication is restored. The VPS deployment can use the checksum-verified committed archive meanwhile.

## Install implementation

The public manifest contains 192px and 512px icons, a stable application ID and standalone display mode. The service worker does not cache app builds, API responses, accounts, contacts or messages. It fetches navigation from the network and provides a static, explicit offline screen if the network fails. Existing server data, authentication, provider gates and permissions are retained.

Do not describe this handoff as complete WATI/Emovur parity or as accepted automatic WhatsApp messaging. Evidence for source tests, browser behaviour, live AI replies and external provider acceptance is recorded separately.
