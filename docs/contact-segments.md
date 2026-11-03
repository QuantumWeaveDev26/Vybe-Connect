# Contact segments

Saved contact segments support all/any conditions on name, phone, tags, marketing consent, conversation status, assignee, source, last inbound time and a custom attribute key. The visual editor supports one all/any group. The API supports up to twenty conditions and three nested levels. Unsupported expressions and regex execution are rejected; criteria are never evaluated as code.

Text comparisons are case-insensitive. Equality preserves primitive types: numeric 90 differs from text "90", and booleans differ from numbers. Numeric ordering accepts finite numeric values. Tag filters use membership or empty/existence conditions. Missing attributes do not match ordinary negative comparisons; use Missing explicitly. Date-only values mean UTC midnight; date-times require an offset. Preview returns counts, opted-in totals, up to 20 samples and up to 1,000 matching contact IDs, with a truncation flag.

Administrators can save/delete segments; authenticated teammates can preview their own workspace. Saved segments are isolated by tenant. No credentials or provider calls are needed to edit and preview.

Campaign drafts can select a saved audience and optionally require a tag. At launch the audience is resolved again from current contact data and consent. Deleted segments cause launch to fail; they never fall back to all contacts. Already queued campaigns retain their enrolled recipients, and the worker rechecks consent before submission. Broader WATI conversation filters, shared visibility controls, unread tracking and exact operator/dialog parity remain incomplete.

REA historical shipped-source inspection established attribute filters and saved-filter operations. It does not establish that this independent rule vocabulary or behavior exactly matches WATI's current UI or backend. Captured WATI code is excluded from the delivered application.
