# Fase 8 — Trazabilidad

| Requisito | Implementación | Evidencia |
|---|---|---|
| Acceso autenticado | Grant opaco con hash y sesión segura | Pruebas de portal y servicio |
| Revocación | Estado y fecha persistentes | Prueba `test_revoke_grant_invalidates_active_access` |
| Aislamiento | Consulta por solicitud y documento | Prueba de autorización documental |
| R2 privado | Descarga mediada en backend | Prueba API de descarga |
| Auditoría | Evento por documento descargado | Prueba de registro de descarga |
| Rollback | Migración `20260804_0004` reversible | CI PostgreSQL obligatorio |
