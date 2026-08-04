# Changelog

## 0.9.0 — 2026-08-04

- Verificación de acceso mediante OTP enviado en mensaje separado.
- Hash ligado al token, caducidad, máximo de intentos y bloqueo temporal.
- Rotación de credencial después de verificar y protección CSRF.
- CSP restrictiva y migración reversible que invalida accesos anteriores.

## [0.8.0] - 2026-08-04

- Portal temporal autenticado mediante credencial opaca almacenada únicamente como SHA-256.
- Sesión `HttpOnly`, `Secure` y `SameSite=Strict`, con expiración y revocación persistentes.
- Descargas mediadas por el backend sin exponer URL firmada ni clave privada de R2.
- Autorización por solicitud y documento, y trazabilidad individual de cada descarga.
- Migración reversible para accesos al portal y eventos de descarga.

## [0.7.0] - 2026-08-04

- Confirmación explícita del gestor mediante folio.
- Entrega al cliente con enlaces privados R2 firmados por 10 minutos.
- Outbox idempotente con reintentos limitados y bloqueo concurrente.
- Estados finales, trazabilidad del ID de Meta y Cron Job de Render.
- Migración reversible para intentos de entrega.

## 0.6.0 - 2026-08-04

- Added authenticated Meta media retrieval and private Cloudflare R2 uploads.
- Added authorization by assigned gestor and association by reply or request folio.
- Added binary signature, extension and 10 MB validation for PDF, JPEG and PNG.
- Added SHA-256 deduplication metadata and 30-day document expiration.
- Added reversible Alembic migration and R2 lifecycle configuration.

## 0.5.0 - 2026-08-04

- Added strict RFC/CURP validation, masking, authenticated hashing and Fernet encryption.
- Added E.164 phone normalization and collision-resistant public folios.
- Added transactional request creation with authorized gestor assignment and audit events.
- Added bounded Meta Graph API delivery with outbound message ID persistence.
- Added recoverable audit state for gestor notification failures.
- Upgraded the production cryptography requirement to 50.0.0 after audit findings.

## 0.4.0 - 2026-08-04

- Added authenticated Meta WhatsApp webhook verification and reception.
- Added strict, content-free metadata parsing and PostgreSQL-backed idempotency.
- Added append-only audit registration for accepted inbound message events.
- Added synthetic security, API, parsing, duplicate, and payload-limit tests.

## 0.3.0 - 2026-08-04

- Landing pública responsive con identidad Gestoría Reaver.
- CTA a WhatsApp configurable y sin datos personales en la URL.
- Modos claro/oscuro, navegación por teclado y reducción de movimiento.
- SEO técnico, sitemap, robots y páginas legales marcadas como preliminares.

## 0.2.0 - 2026-08-04

- Modelo PostgreSQL normalizado y migración Alembic inicial.
- Máquina de estados explícita y control de concurrencia optimista.
- Idempotencia de mensajes, deduplicación documental y auditoría append-only.
- Pruebas de migración PostgreSQL en CI y migración controlada en Render.

## 0.1.0 - 2026-08-04

- Estructura modular inicial de FastAPI.
- Configuración validada para PostgreSQL.
- Health checks de vida y disponibilidad.
- Logging JSON con redacción de campos sensibles.
- Pruebas automatizadas, controles de calidad y CI.
- Blueprint inicial para Render.
# 0.10.0

- Cuarentena obligatoria y análisis antimalware con ClamAV antes de entregar.
- Reintentos de escaneo persistentes y bloqueo seguro de resultados dudosos.
- API administrativa operativa con token protegido y datos sanitizados.
- Worker programado y migración reversible para metadatos de análisis.
