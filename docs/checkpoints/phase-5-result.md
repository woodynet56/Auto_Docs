# Phase 5 checkpoint

## Implemented

- Privacy-preserving RFC/CURP handling.
- Phone normalization and public folios.
- Transactional creation and active-gestor authorization.
- Meta notification with bounded retry and outbound message ledger.
- Recoverable notification-failure audit event.
- Synthetic unit, API and security tests.

## Not implemented

- Document reception or storage.
- Automated delivery recovery/outbox worker.
- Client confirmation and final delivery.
- Administrative gestor management.

## Local validation

- Ruff: approved.
- Ruff format: approved.
- MyPy strict: approved.
- Pytest: 62 passed, 1 PostgreSQL test skipped.
- Coverage: 85.52%.
- Bandit: zero findings.
- Dependency audit: rejected local cryptography 46.0.0; production pin raised to 50.0.0.

The exact cryptography 50.0.0 install and PostgreSQL transaction tests must pass in GitHub Actions.
Production deployment is blocked if either control fails.

## Manual test

1. Configure only synthetic Meta credentials and an active gestor in staging.
2. Send `SOLICITUD: <synthetic RFC>` from a test number.
3. Expect one request with an assigned gestor and a valid `REQ-YYYYMMDD-XXXXXX` folio.
4. Verify the gestor receives only the folio and masked identifier.
5. Replay the webhook and verify that no second request is created.
6. Invalidate Meta delivery and verify `request.gestor_notification_failed` is appended.

Rollback: deploy version 0.4.0. This phase adds no database migration; rows created under 0.5.0
remain compatible with the Phase 2 schema.
