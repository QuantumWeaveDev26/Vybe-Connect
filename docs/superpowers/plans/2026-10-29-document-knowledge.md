# Document knowledge and grounded retrieval

Continue inline with the current Python/SQLite application and test-driven development. Keys and live-provider verification remain deferred at the user's request.

Design: administrator uploads UTF-8 TXT, Markdown, CSV or DOCX; bounded local parsing stores workspace-isolated text chunks and file metadata. Binary/PDF extraction is explicitly unsupported in this increment. Local lexical retrieval chooses up to six relevant passages instead of blindly putting every document in the prompt. Generated knowledge references must match passage identifiers actually supplied to the model. A source viewer retrieves current tenant-scoped passages. Disable/delete excludes a document from later requests. No embeddings, external crawling or paid API calls are needed for indexing.

- [x] Write ingestion, tenant isolation, duplicate upload, parser bounds and retrieval relevance tests.
- [x] Implement knowledge_documents.py, persistence and authenticated upload/source endpoints.
- [x] Add document passages and validated citations to AI chat context and structured answers without changing legacy manual knowledge semantics.
- [x] Add upload, enable/disable/delete and source viewer controls, with scope checks on asynchronous responses.
- [x] Run the local suite, package sources and restart the app. Preserve database, credentials and live gates; disclose remaining extraction and parity gaps.

Local verification: 145 tests, JavaScript syntax, Python compilation and renderer/privacy checks passed. Provider transports were mocked; no live or paid calls occurred. Current visual acceptance, independent final review and complete WATI parity remain unverified.
