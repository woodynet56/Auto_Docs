# Phase 5 threat model

| Threat | Control | Residual risk |
|---|---|---|
| RFC/CURP disclosure | In-memory parsing, encryption at rest, HMAC-SHA256 lookup, masking | Process memory is trusted |
| Identifier guessing | Keyed hash instead of a plain digest | Key rotation procedure remains pending |
| Unauthorized assignment | Active gestor lookup by configured E.164 number and role | Gestor administration arrives in Phase 8 |
| Duplicate creation | Existing webhook provider-message uniqueness boundary | Concurrent PostgreSQL test runs in CI |
| Meta token exposure | Secret settings and generic exceptions | Operational secret rotation is pending |
| Network failure | Timeout, bounded retries and recoverable audit event | Automated recovery is Phase 7 |
| Sensitive logging | No identifier, body, token or provider response logging | Production log review remains required |

The full identifier is not included in audit metadata, outbound notifications, API responses or
model representations. The notification contains the folio and masked identifier only.
