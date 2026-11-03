# Saved contact segments and campaign targeting

Continue inline with TDD. REA historical captures establish attribute-based filtering and saved conversation filter operations, but do not establish the complete WATI operator vocabulary or current filter dialog. Implement bounded all/any contact criteria over existing contact fields and custom attributes, with typed comparison and no executable expressions. Add a visual rule editor, local preview and saved segment management. Campaign audiences resolve saved criteria at launch and still require consent and normal provider gates. Segment deletion before launch must fail closed. Keys remain deferred.

- [x] Test typed matching, all/any groups, malformed criteria, role/tenant isolation and dynamic campaign enrollment.
- [x] Implement contact_segments.py and persist saved segments; connect the audience helper to campaign save/launch.
- [x] Add visual criteria editing, previews, saved segments and campaign audience selection.
- [x] Run regression checks and update coverage evidence. Do not invoke live providers or copy WATI source into the deliverable.

Release evidence: full suite 164 tests passed; Python compilation, JavaScript syntax and renderer checks passed. No live provider calls, webhook deliveries or paid usage occurred. Independent final review and current visual acceptance remain unavailable after the prior workspace credit limit. Exact parity remains incomplete.
