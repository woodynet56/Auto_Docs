# Punto de control — Fase 8

El portal autenticado y revocable reemplaza los enlaces R2 enviados directamente en la Fase 7.
La compatibilidad se conserva en el outbox y en sus reintentos, pero toda entrega nueva genera
un único enlace al portal. El despliegue requiere `PUBLIC_BASE_URL` HTTPS correcto y la migración
`20260804_0004`. Para rollback, detener entregas, volver al artefacto 0.7.0 y ejecutar el
downgrade solo después de preservar la evidencia de acceso exigida por la política aplicable.

## Evidencia local

- 96 pruebas aprobadas y 1 prueba PostgreSQL omitida por falta del servicio externo.
- Cobertura total: 86.85 %.
- Ruff, formato, MyPy estricto, Bandit y auditoría de dependencias aprobados.
- Compilación Python, smoke test y Blueprint de Render aprobados.
- La ejecución Alembic/PostgreSQL permanece como control obligatorio de CI.
