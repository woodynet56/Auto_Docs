# Phase 4 checkpoint

## Implemented

Meta webhook verification, raw-body signature validation, defensive parsing, idempotent inbound
message registration, minimal append-only audit metadata, request-size limit and synthetic tests.

## Explicitly not implemented

Creating service requests, interpreting message text, downloading media, sending Meta messages,
document storage, gestor authorization, queues, rate limiting or production Meta configuration.

## Manual verification

1. Configure synthetic `WA_VERIFY_TOKEN` and `WA_APP_SECRET` locally.
2. GET `/webhooks/meta/whatsapp` with the three `hub.*` parameters; expect the exact challenge.
3. POST a synthetic payload signed over its exact bytes; expect `accepted: 1`.
4. Repeat the identical provider ID against PostgreSQL; expect `duplicates: 1`.
5. Modify the body without recalculating the signature; expect HTTP 401.

## Rollback

Revert the Phase 4 files and application router registration. No schema migration was introduced;
the Phase 2 `whatsapp_messages` and `audit_events` tables remain compatible.
