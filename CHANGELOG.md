# Changelog

## 0.12.2 - 2026-08-07

- Added executable Spanish Gherkin acceptance criteria with `pytest-bdd`.
- Added a single-command local/CI quality gate and durable JUnit/coverage evidence.
- Added the mandatory QA procedure, severity policy and GO/NO-GO criteria.
- Made Gherkin acceptance and PostgreSQL migration validation blocking in GitHub Actions.

## 0.11.0 - 2026-08-04

- Replaced the shared administrative bearer token with OIDC Authorization Code SSO.
- Added encrypted, expiring administrative sessions and CSRF protection.
- Added viewer, operator and security-admin role hierarchy based on OIDC groups.
- Added a responsive operational dashboard with sanitized quarantine metadata.
- Added SSO threat model, alert thresholds, rollback and preproduction checklist.

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
# 0.12.0 - 2026-08-04

- Certificación reproducible de preproducción mediante GitHub Actions.
- PostgreSQL 17 real para migraciones y suite automatizada.
- Perfil k6 con umbrales explícitos de error y latencia.
- OWASP ZAP baseline bloqueante para seguridad dinámica.
- Respaldo PostgreSQL cifrado con AES-256-GCM y manifiesto SHA-256.
- Restauración protegida y exclusiva para bases aisladas.
- Objetivos RPO/RTO, simulacro de recuperación y dictamen GO/NO-GO.
- Matriz de resiliencia para PostgreSQL, Meta, R2, ClamAV y OIDC.
## 0.12.1 - 2026-08-05

- Preparación reproducible del repositorio para GitHub y Render.
- Blueprint enlazado a PostgreSQL interno con migración previa y health check de disponibilidad.
- Dominio de preproducción configurado para `auto-docs-kv9o.onrender.com`.
- CTA público y número empresarial de WhatsApp configurados para `+52 55 6580 8766`.
- CI automático para cada push a `main`, compatible con `autoDeployTrigger: checksPass`.
- Inclusión segura de `.gitignore` y `.env.example`, sin credenciales reales.
# 0.13.0 - 2026-08-08

- Se separaron clientes operativos y gestores externos de los usuarios del portal.
- Se incorporaron clientes `FIXED` y `RANDOM`, con alta automática por teléfono.
- La recepción acepta lenguaje natural y referencias flexibles; RFC/CURP ya no bloquean solicitudes.
- La asignación prioriza tipo documental, después horario y finalmente respaldo.
- La respuesta del gestor se correlaciona por mensaje citado o `REQ-ID`.
- El primer archivo limpio se entrega automáticamente al propietario y completa la solicitud.
- Se permiten PDF, JPEG, PNG, XML y DOCX; ZIP genérico permanece bloqueado hasta inspección segura.
- Se agregó la migración compatible `20260808_0007` y escenarios Gherkin del flujo operativo.
