# Phase 4 traceability

| Requirement | Component | Test | Result |
|---|---|---|---|
| GET verification | `app/api/webhooks.py` | `test_get_verification_*` | Approved |
| HMAC signature | `app/core/security.py` | `test_meta_signature_*`, negative API test | Approved |
| Safe parsing | `app/services/webhook_parser.py` | `test_webhook_parser.py` | Approved |
| Idempotency | `whatsapp_messages` unique ID and repository | `test_post_is_authenticated_and_idempotent` | Approved |
| Event registration | `app/repositories/webhook_events.py` | API acceptance test; PostgreSQL migration CI | Locally partial |
| Synthetic payloads | `tests/api/test_webhooks.py` | Complete Phase 4 suite | Approved |
| Body limit | `app/api/webhooks.py` | oversize API test | Approved |
