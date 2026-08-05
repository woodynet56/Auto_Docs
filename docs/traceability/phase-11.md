# Fase 11 — trazabilidad

| Requisito | Implementación | Evidencia |
|---|---|---|
| SSO individual | OIDC Authorization Code y `userinfo` | `admin_identity.py` y pruebas unitarias |
| RBAC | Jerarquía viewer/operator/security_admin por grupos | Pruebas de mapeo y denegación |
| Sesión segura | Cookie cifrada, Secure, HttpOnly, SameSite Strict y TTL | Pruebas de cifrado, expiración y alteración |
| Panel visual | Resumen y cola sanitizada | `admin.html`, `admin.js` y API `/admin/api` |
| Acción privilegiada | Rol operator y CSRF | Pruebas API de rechazo |
| Operación | Umbrales, runbook y rollback | checkpoint y modelo de amenazas |

La API no devuelve RFC, CURP, teléfonos, nombres de archivo, hashes, claves R2, OTP ni contenido.
