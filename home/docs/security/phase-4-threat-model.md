# Phase 4 threat model

| Threat | Control in this increment | Residual risk |
|---|---|---|
| Spoofed Meta request | HMAC-SHA256 over the exact raw body and constant-time comparison | Secret rotation remains operational |
| Replay or duplicate webhook | Unique provider message ID plus transactional insert | Cross-region queue design is deferred |
| Tampered verification | Exact mode, non-empty configured token, constant-time token comparison | Meta account setup is pending |
| Parser abuse | Maximum body size, strict JSON, bounded fields and allowed message types | Rate limiting is Phase 9 |
| Sensitive-data leakage | Content and full payload are never persisted or logged | Database fields still require production access controls |
| Ambiguous or unsupported event | Safely acknowledged as ignored without business action | Monitoring thresholds are deferred |
| Duplicate concurrent insert | PostgreSQL uniqueness boundary and rollback | Full concurrency test runs in CI with PostgreSQL |

Privacy-by-design decision: Phase 4 retains only provider ID, routing phones, message type,
optional quoted-message ID, processing status and timestamps. Message text, captions, media bytes,
access tokens and raw webhook payloads are excluded. No request or document workflow is triggered yet.
