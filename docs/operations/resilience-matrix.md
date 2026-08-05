# Matriz de resiliencia

| Dependencia | Fallo inyectado | Comportamiento esperado | Alerta | Recuperación |
|---|---|---|---|---|
| PostgreSQL | conexión rechazada/timeout | readiness 503; sin aceptar trabajo persistente | inmediata | reconexión y verificación de cola |
| Meta | 429/500/timeout | outbox pendiente; reintento idempotente; sin cierre falso | 5 min | backoff y replay controlado |
| R2 | 403/500/timeout | sin descarga ni entrega; error sanitizado | inmediata | corregir acceso y reintentar |
| ClamAV | timeout/firma vieja | documento en cuarentena; nunca limpio por omisión | 2 min | actualizar firmas y reprocesar |
| OIDC | issuer/JWKS no disponible | acceso administrativo cerrado; sesiones válidas expiran normalmente | 5 min | recuperar proveedor y reautenticar |

Cada ejercicio debe registrar hora de inicio, detección, mitigación, recuperación, pérdida de
datos observada y responsable. Está prohibido inyectar fallos en producción sin un procedimiento
aprobado y una ventana comunicada.
