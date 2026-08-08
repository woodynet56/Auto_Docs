# Fase 8 — Modelo de amenazas del portal

## Activos protegidos

- Documentos privados en R2.
- Credenciales temporales del portal.
- Relación entre cliente, solicitud y documentos.
- Historial individual de descargas.

## Controles

- El token tiene 256 bits aleatorios y solo se persiste su hash SHA-256.
- Cada nueva entrega rota el token anterior; la revocación se guarda en PostgreSQL.
- La sesión se limita a `/portal` y usa `HttpOnly`, `Secure` y `SameSite=Strict`.
- Las respuestas privadas usan `Cache-Control: no-store`, `Referrer-Policy: no-referrer`,
  `X-Frame-Options: DENY` y `X-Content-Type-Options: nosniff` en descargas.
- La autorización comprueba grant, solicitud, documento, estado, expiración y clave privada.
- R2 se consulta desde el backend; el navegador nunca recibe una URL firmada de R2.
- La trazabilidad no conserva token, IP, agente de usuario ni claves de almacenamiento.

## Riesgo residual

El enlace inicial de WhatsApp es una credencial al portador hasta su canje o revocación. Debe
usarse exclusivamente sobre HTTPS, con registros de proxy que redacten parámetros sensibles.
Una segunda autenticación independiente puede añadirse si la evaluación jurídica lo exige.
