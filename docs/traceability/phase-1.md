# Trazabilidad — Fase 1

| Requisito | Componente | Prueba | Estado |
|---|---|---|---|
| RF-022: liveness | `app/api/health.py` | `test_liveness`; smoke test | Aprobado |
| RF-022: readiness PostgreSQL | `app/api/health.py` | `test_readiness_when_database_*`; smoke test | Aprobado |
| Configuración PostgreSQL | `app/core/config.py` | `test_settings_reject_non_postgresql_database` | Aprobado |
| Logging sin secretos | `app/core/logging.py` | `test_formatter_redacts_sensitive_context` | Aprobado |
| CI obligatorio | `.github/workflows/ci.yml` | Validación local equivalente | Aprobado |

## Evidencia

- 12 pruebas aprobadas.
- Cobertura: 91.10 % (umbral: 85 %).
- Ruff, formato y MyPy estricto: aprobados.
- Bandit: cero hallazgos.
- Pip-audit: cero vulnerabilidades conocidas en dependencias publicadas.
- Compilación Python: aprobada.
- Smoke test: `/` 200, `/health/live` 200 y `/health/ready` 503 sin PostgreSQL.
