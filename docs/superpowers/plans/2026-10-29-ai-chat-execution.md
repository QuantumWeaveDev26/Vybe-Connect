# AI chat execution parity increment

REA observed WATI Ask while a user-started request was executing: reading conversations, elapsed time, Append message and Stop controls (`ev_1b3cebc93989d1640cf0e28d8ed6653bcff928ef50cf6ade5b5454f65709c48c`). These are workflow requirements, not justification for decorative progress or a false stop result.

- [x] Capture the exact mode menu without sending new WATI prompts. Change local modes only when their actual WATI labels/behavior are observed.
- [x] Write failing tests, then implement workspace/user-private durable chat jobs, per-chat ordering, bounded append queue, truthful execution phases, cancellation before provider submission and provider-confirmed cancellation afterward.
- [x] Use OpenAI background Responses with `store:false` and official retrieve/cancel endpoints. Persist provider IDs and never resubmit an uncertain create after a crash. Local Ollama cancellation only discards a late answer; disclose that provider generation cannot be confirmed stopped. All provider paid gates remain enforced.
- [x] Add a separate job worker, UI elapsed timer, Append message and Stop states, preserving chat/user/workspace identity. Prevent replies from overwriting changed chat history.
- [x] Run domain/HTTP/provider/renderer regressions and independent review; update acceptance gaps and clean ZIP. No live inference, WATI message sends, settings changes or paid calls during verification.

Official reference: https://developers.openai.com/api/docs/guides/background — background requests support store:false, temporary provider storage for polling, retrieval, and idempotent cancellation. Provider cancellation and locally discarding an answer are distinct outcomes. Full WATI backend, visual and broader product parity remains incomplete.

Implementation notes: mode choices came from passive loaded-source capture rather than a rendered menu. Independent review covered the AI job increment before later media/commerce integration; no final independent review was possible after the workspace credit limit. Local tests cover those later services. Full product parity remains incomplete.
