# Gestoría Reaver 0.12.0

Versión actual: **0.12.0**. La base funcional incorpora SSO OIDC, RBAC, cuarentena y portal
reforzado. Esta fase añade certificación reproducible de preproducción, carga, DAST y respaldo
cifrado con restauración ensayable. El paquete está técnicamente preparado, pero su liberación
permanece condicionada a obtener la evidencia externa detallada en
`docs/checkpoints/phase-12-result.md`.

Versión 0.8.0: base técnica, dominio, landing, webhook Meta, solicitudes, gestión documental,
entrega confirmada y portal temporal autenticado con descargas revocables y auditadas.

Versión 0.6.0: base técnica, modelo de dominio, landing pública, webhook autenticado, creación
controlada de solicitudes y recepción privada de documentos por WhatsApp. La entrega documental
y el panel aún no están implementados.

Aplicar el esquema con `alembic upgrade head`. Render ejecuta esta migración como paso previo
controlado antes de iniciar una nueva versión.

## Requisitos

- Python 3.12
- PostgreSQL 16 o superior

## Ejecución local

```bash
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Verificación:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

La landing está disponible en `http://localhost:8000/`. Para activar su CTA configure
`PUBLIC_WHATSAPP_NUMBER` con 8 a 15 dígitos, sin `+`, espacios ni datos del cliente. El aviso de
privacidad y los términos publicados son borradores informativos y deben recibir aprobación
legal antes del tratamiento de datos reales.

`/health/live` comprueba el proceso. `/health/ready` devuelve 503 si PostgreSQL no está disponible.

## Calidad

```bash
ruff check .
ruff format --check .
mypy app tests
pytest --cov=app --cov-report=term-missing --cov-fail-under=85
bandit -c pyproject.toml -r app
pip-audit -r requirements.txt
python -m compileall -q app
python scripts/smoke_test.py
```

La certificación manual de GitHub Actions ejecuta además PostgreSQL 17, OWASP ZAP y k6 contra
una URL HTTPS de preproducción explícita. No debe apuntarse a producción.

## Continuidad

Los scripts `scripts/backup_database.py` y `scripts/restore_database.py` crean respaldos
PostgreSQL cifrados y ejecutan simulacros únicamente contra una base aislada. Consulte
`docs/operations/backup-restore.md`. Objetivos iniciales: RPO de 60 minutos, RTO de 120 minutos y
retención de 35 días; deben validarse mediante un simulacro real antes de liberar.

La prueba de humo espera `root=200`, `live=200` y, si PostgreSQL local no está iniciado,
`ready=503`. Este último resultado confirma que la aplicación falla de forma segura.

## Despliegue

El archivo `render.yaml` crea un servicio web y PostgreSQL. Antes de desplegar, revise región y
planes, conecte el repositorio de GitHub y confirme que las comprobaciones de CI estén aprobadas.
Los secretos de WhatsApp y Cloudflare R2 se configuran exclusivamente como variables protegidas.

## WhatsApp y solicitudes

Configure `WA_VERIFY_TOKEN`, `WA_APP_SECRET`, `WA_PHONE_NUMBER_ID`, `WA_ACCESS_TOKEN`,
`WA_BUSINESS_PHONE_NUMBER`, `GESTOR_PHONE_NUMBER`, `IDENTIFIER_ENCRYPTION_KEY` e
`IDENTIFIER_HASH_KEY` como secretos. Meta debe usar:

- Verificación y recepción: `https://SU-DOMINIO/webhooks/meta/whatsapp`
- Encabezado POST obligatorio: `X-Hub-Signature-256`

El comando de creación es `SOLICITUD: <RFC-o-CURP>`. Su contenido se procesa solo en memoria; el
identificador se almacena cifrado, con hash HMAC y enmascarado. No se persisten textos, captions,
payloads completos. Las pruebas utilizan números, IDs y contenido sintéticos.

## Documentos privados

Configure `R2_ENDPOINT_URL`, `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID` y `R2_SECRET_ACCESS_KEY`.
El bucket debe permanecer privado y debe aplicarse `infra/r2-lifecycle.json` para eliminar los
objetos bajo `requests/` después de 30 días. Se admiten PDF, JPEG y PNG de hasta 10 MB. El gestor
asignado debe responder a un mensaje asociado a la solicitud o incluir el folio exacto en el
caption. El sistema valida la firma binaria y nunca incorpora el nombre original a la clave R2.

## Portal seguro

Configure `PUBLIC_BASE_URL` con el dominio HTTPS definitivo, `PORTAL_SESSION_TTL_MINUTES` entre
5 y 1440, y mantenga `PORTAL_COOKIE_SECURE=true` en producción. WhatsApp recibe un único acceso
personal al portal; la credencial se guarda en PostgreSQL solo como SHA-256 y se intercambia por
una cookie `HttpOnly`, `Secure` y `SameSite=Strict`. El backend valida nuevamente solicitud,
documento, vigencia y revocación antes de descargar desde R2. Cada descarga autorizada produce
un evento individual sin IP, agente de usuario, URL firmada ni clave de almacenamiento.

## Cuarentena y operación administrativa

Configure `CLAMAV_HOST`, `CLAMAV_PORT` y `ADMIN_API_TOKEN` como variables protegidas. Todo archivo
nuevo se almacena con estado `quarantined`; el worker `scripts.scan_quarantine` lo obtiene desde
R2 por el backend y utiliza el protocolo `INSTREAM` de ClamAV. Solo `clean` puede avanzar hacia
confirmación y entrega. Un resultado infectado queda bloqueado y un resultado indeterminado se
reintenta hasta el máximo configurado, tras lo cual se rechaza de forma segura.

La API `/admin` no se publica en OpenAPI y requiere `Authorization: Bearer <token>`. El resumen y
la cola de cuarentena excluyen teléfonos, RFC/CURP, nombres de archivo, hashes, claves R2, OTP y
credenciales. El token debe generarse aleatoriamente, rotarse mediante el gestor de secretos y
no reutilizarse en otros sistemas.

El logo original está en `app/static/brand/`; las plantillas y recursos públicos están separados
en `app/templates/` y `app/static/`.

## Decisiones bloqueantes

- Aviso de privacidad y base jurídica para datos reales.
- Cuenta/número/plantillas aprobadas de Meta WhatsApp.
- Reglas de asignación de gestores.
- Confirmación y cierre definitivo de solicitudes.
