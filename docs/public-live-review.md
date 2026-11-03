# Token-free live review

The optional `TW_PUBLIC_REVIEW=true` setting makes the public homepage open a read-only review workspace after an unauthenticated state request. Owner setup and sign-in remain at `/owner`. A valid owner session still opens the real workspace on the homepage. Production setup continues requiring its private token; public visitors cannot claim the installation.

The review store lives in a separate temporary directory. It contains labelled example agent configurations, business knowledge, one reserved-number example contact, an internal sample note and a disabled example webhook connection. It contains no copied customer records. Its setup session is deleted immediately and no session cookie is issued to review visitors. Its workers never run. Main-store sessions, credentials and data are not exposed through review endpoints.

Only explicitly allowlisted review GET resources exist. Write requests to review routes return 403. Real API routes retain normal authentication. Frontend saves are also blocked with a read-only explanation; the backend boundary does not depend on that frontend check. AI and live messaging indicators in review remain disconnected. This is an interface review, not evidence of live delivery or model quality.

Set `TW_PUBLIC_REVIEW=false` and recreate only the `vybe-connect` app project to remove public review after acceptance. No customer database deletion, account reset or provider change is needed. Review data is ephemeral and is not a business backup.

This increment also replaces the hover-expanding sidebar with a keyboard-accessible expand/collapse control that reserves layout space and remembers the preference. The previous hover overlay could cover card buttons. Route changes now start the page at the top.

Validation: 488 Python tests passed in 226.578 seconds, plus Node renderer/privacy and directory tests. Browser checks covered all 12 primary sections, agent edit form access, blocked saves and navigation expansion. REA inspected the current authorized WATI Astra screen (`ev_925479e80b776b7488bd0ba592028117b7ef468c5d6553a506530b8be3c3591a`). Its active click provider returned an execution failure, so unobserved WATI workflows remain unverified.

Full WATI parity, calling, complete commerce, public client onboarding/billing, broader knowledge retrieval, live-provider acceptance, load/restore drills and operational sign-off remain unfinished. Enabling review mode does not clear those release gates.
