# Chatbot contact actions

The visual builder now includes Set a custom attribute, Remove a tag and Assign a teammate. These nodes are supported in saved and imported TeamWave JSON graphs and can run after a question, condition or persistent wait. WATI JSON exports still require a separate converter.

Set-attribute uses a custom field name of up to 60 letters, digits, spaces, underscores or hyphens. Its text value accepts the existing `{{name}}` and saved-variable substitutions, including an empty value. Raw and expanded values must fit 1,000 characters. It cannot change phone, consent, identity or protected contact fields.

Remove-tag matches case-insensitively and is harmless if the tag is absent. Assign-teammate selects one current workspace member and continues the flow. Use a separate Human handoff node to pause automation. Membership is checked when saving and before every execution/continuation, including assignments on branches that may not run.

Each continuation computes on a copy before saving any contact changes or drafts. It enforces 25 tags, 50 custom attributes, 10,000 serialized attribute characters and 4,096 characters per expanded message. Existing tag values are preserved rather than truncated to admit an extra tag.

If membership or capacity prevents execution, that continuation's changes/drafts are discarded, the inbound message is retained, status becomes Pending, automation pauses and both the active flow session and accepted-reply watch are removed. An internal note and `flow_last_event` explain why. The timer records a blocked outcome and does not retry. Resuming automation does not revive the cancelled session. Changes committed by previous continuations remain.

This increment follows the node vocabulary observed in earlier read-only REA captures. On 2 November the REA Chrome endpoint was unreachable; automatic approval review blocked reopening the remote-debugging browser. No fresh WATI visual/runtime comparison was obtained. Draft mode remains unsent. Gated live text/media/supported-template graph transport is implemented separately; full WATI graph vocabulary and immutable published graph versions remain incomplete.

REA static refresh on the saved capture returned parent Evidence `ev_3b0813f81e3389d9964a1e747c97d8401b514d809bd0a81070e30214f6dd9b7b` and summary `ev_dcf638f146e0bf1ee6fc99ae8980986c9b54f2e35585f42bb24d1998368b2fd7`. Selected assignment-modal and attribute-field sources were requested as inert JavaScript. Coverage remains partial: unselected sources and node/unknown retention ceilings prevent full application conclusions. It does not establish live behavior, exhaustive feature coverage or equality.
