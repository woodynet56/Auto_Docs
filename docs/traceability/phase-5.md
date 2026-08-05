# Phase 5 traceability

| Requirement | Component | Test | Result |
|---|---|---|---|
| Validate RFC/CURP | `services/identifiers.py` | `test_rfc_and_curp_validation_and_normalization` | Approved |
| Encrypt, hash and mask identifier | `services/identifiers.py` | `test_mask_encrypt_hash_and_decrypt` | Approved |
| Normalize phone | `services/phones.py` | `test_phone_normalization` | Approved |
| Generate folio | `services/folios.py` | `test_folio_format_and_randomness` | Approved |
| Create and assign request | `repositories/requests.py` | PostgreSQL CI integration | Pending external CI |
| Notify gestor without full identifier | `services/requests.py` | `test_request_command_creates_notifies_and_records_message` | Approved |
| Record Meta message ID | `repositories/requests.py` | Service contract test plus PostgreSQL CI | Partially approved |
| Record recoverable delivery failure | `services/requests.py` | `test_delivery_failure_is_recorded_as_recoverable` | Approved |
| Bound Meta retries | `services/whatsapp.py` | `test_meta_client_retries_timeout` | Approved |
| Reject vulnerable crypto release | `pyproject.toml` | `pip-audit` in CI | Pending exact-version CI |
