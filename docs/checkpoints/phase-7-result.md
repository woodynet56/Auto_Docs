# Fase 7 — Resultado

Versión: 0.7.0. Alcance: confirmación explícita, entrega segura, outbox, reintentos y cierre.

## Contrato funcional

- Solo el gestor activo asignado puede enviar `CONFIRMAR <folio>`.
- La solicitud debe estar en `documents_received` y tener documentos vigentes.
- Los objetos siguen privados; se generan URLs AWS SigV4 con vigencia máxima de 15 minutos.
- La solicitud solo pasa a `completed` cuando Meta devuelve un identificador de mensaje.
- Un outbox único por solicitud impide duplicados y conserva errores mediante códigos sanitizados.
- El Cron Job reclama filas con `FOR UPDATE SKIP LOCKED` cada cinco minutos.

## Evidencia local

- 87 pruebas aprobadas y una integración PostgreSQL omitida por falta del servicio externo.
- Cobertura: 87.27 %.
- Ruff, formato y MyPy estricto aprobados.

## Rollback

Detener el Cron Job, desplegar 0.6.0 y ejecutar `alembic downgrade 20260804_0002`. Los objetos R2
no se eliminan por el rollback y continúan sujetos a la retención de 30 días.
