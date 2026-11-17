# Repository adoption — 17 November 2026

Only small compatible utilities were adapted into the existing Python application. Original reference files, license text and attribution are retained under `third_party/`; no upstream WhatsApp service was installed or activated.

| Source | Pinned revision | Adopted behavior |
| --- | --- | --- |
| [OpenWA](https://github.com/rmyndharis/OpenWA) | `258f27411d7305c2e92338ef8b5e4ba2f69cd389` | MIT placeholder rendering adapted in `text_templates.py`, with bounded output and existing single-brace compatibility. |
| [MultiWA](https://github.com/ribato22/MultiWA) | `704c1c4bc1b845f12c9d03f2ac2747d3475b577e` | MIT bounded page-size normalization adapted in `listing_limits.py` for call history. |
| [Chatwoot](https://github.com/chatwoot/chatwoot) | `00d4855180c351ebd3c9bd64f61acc9332b14a0b` | Community MIT conversation-context selection adapted in `ai_context.py`; no enterprise code copied. |

[Typebot](https://github.com/baptisteArno/typebot.io) was reviewed but not copied: its reviewed current FSL-1.1-Apache-2.0 terms restrict competing hosted commercial use before the applicable change date. [Evolution API](https://github.com/evolution-foundation/evolution-api) was reviewed but not integrated: its reviewed modified Apache license adds branding/notification conditions, and QR-linked WhatsApp sessions require an independently reviewed operational integration. Neither is a license-free shortcut. License compatibility does not establish live WhatsApp acceptance or account safety.

The utilities are covered by `tests/test_repo_adaptations.py` plus integration cases for unsent saved replies, bounded customer context and paginated call history. They do not replace VYBE's current tenant isolation, billing, provider gates or credential handling.
