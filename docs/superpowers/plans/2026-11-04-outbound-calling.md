# Inbound and outbound WhatsApp calling

Implement outbound calling beside the existing inbound adapter. Calling activation remains separate from approved OpenAI activation; no paid test calls or permission messages.

1. Add permission-state reads, reviewed permission requests within the customer-service window, and outbound connect with a durable request ID. Require provider-confirmed start_call permission immediately before connecting. Unknown provider outcomes never retry automatically.
2. Bind every call to workspace, contact and initiating teammate. Store private SDP separately from public state. Signed connect answers complete outgoing WebRTC negotiation; terminal events win races.
3. Add permission, dial and end controls and browser audio cleanup. Preserve inbound claim handling and disabled-by-default outbound gate.
4. Test provider contracts and failure/race/isolation paths with mocks, then deploy and read back without sending messages or placing calls.

References: PyWa primary API source (get_call_permissions/initiate_call) and Meta documentation links embedded there. Meta documentation fetch was throttled. No claim of live call acceptance until eligible Meta configuration and an authorized real call test.
