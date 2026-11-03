# Deployment boundary and packaging

Continue inline against the existing Python/SQLite checkout. Preserve localhost defaults and current data/secrets. Add a production configuration requiring an exact HTTPS public origin, explicit bind address and protected fresh-owner token. Host and Origin checks use configured authority rather than untrusted forwarding headers. Production cookies use Secure; local HTTP cookies retain current behavior. Add coarse live/DB readiness routes without exposing paths or keys. Keep provider gates unchanged.

Package Docker/Caddy single-instance topology with a persistent private data volume, no directly published app port, no secrets in image/build context and a documented stopped-app backup/restore workflow. Do not claim Docker/image/TLS verification if no engine/domain is available. This is a deployment foundation, not completion of the competitor feature scope or full WATI parity.

- [x] Write failing HTTPS boundary, startup validation, setup-token, health and local-compatibility tests.
- [x] Implement config and HTTP boundaries, secure cookies and private data path setting.
- [x] Add container/proxy configuration and backup validation tools.
- [x] Verify, document remaining release gates and refresh local package.

Local verification: 394 tests passed in 154.625 seconds, Node/UI and compilation passed, restarted loopback HTTP checked. Container/public TLS and broader production acceptance remain unverified; the complete goal remains active.
