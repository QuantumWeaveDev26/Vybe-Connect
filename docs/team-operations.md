# Teams, availability and private collaboration

Open **Settings > Team & user management**. Administrators can create named teams, choose current workspace members and archive teams. Version checks reject stale edits. Removing a member also removes their team memberships and availability. Teams organize routing and do not restrict existing conversation visibility.

Use **Set my availability** for your own status. Available lasts 15-480 minutes, then becomes Away for routing. Away/offline lasts until changed. This is an explicit routing preference, not browser online presence. Availability is separate for each workspace and never changes existing assignments.

## Routing and assignment history

Customer AI can use a manual pool or a managed team's current membership, with least-busy or round-robin distribution. Optional availability requirements and Open/Pending workload caps restrict new assignments. Existing active assignees are preserved. Default policies retain previous behavior. If a strict team/availability/capacity policy has nobody eligible, handoff stays unassigned for human triage instead of falling back outside that policy. Workload selection and assignment run in one transaction.

An unassigned conversation offers **Route unassigned chat**. This puts it under human control and attempts the selected policy. If nobody qualifies, retry later or assign manually; automatic backlog redistribution is not implemented. Clear an existing owner before team routing. Archiving affects future routing, not existing owners.

**Recent assignments** records new manual changes, takeover, team routing, AI handoffs, approved AI assignment findings, rules, chatbots and member removal. It shows up to ten entries from the latest 100 workspace changes. Earlier history cannot be reconstructed. Workload counts Open/Pending chats, not presence or actual response speed.

## Private comments and mentions

Use **Comment / mention teammate** in the conversation inspector. This creates an internal note with an author and one in-app notification per explicitly selected teammate. Duplicate mentions are collapsed. Self-mentions do not notify. Free-text @names alone do not notify. All recipients must still belong to the workspace when the note commits; invalid recipients roll back the note.

**Mentions** in the sidebar shows your latest 50 workspace notifications. Open a conversation from a notification to mark it read. Only that recipient can mark it read. Notes remain visible under the existing workspace inbox permissions; selecting a recipient does not create a private sub-conversation. No WhatsApp message, email or push alert is sent. Internal notes remain excluded from customer-AI context, and live note submissions and ambiguous note/live flag types are rejected.

Legacy or automation-generated notes without authorship metadata retain their previous display. Comment editing/deletion, email/push alerts, browser presence, business hours, collaborator visibility and automatic backlog redistribution remain separate work. Local tests do not establish real browser/device acceptance or full WATI/respond.io equivalence. No actual account teams, availability, comments or provider settings were changed during development.
