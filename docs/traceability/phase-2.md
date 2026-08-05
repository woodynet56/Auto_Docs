# Trazabilidad de Fase 2

| Requisito | Componente | Prueba | Resultado |
|---|---|---|---|
| Usuarios y roles | `app/db/models/user.py` | `test_models.py` | Aprobado |
| Solicitudes e identificadores seguros | `app/db/models/request.py` | modelos y migración | Unitario aprobado; PostgreSQL en CI |
| Máquina de estados | `app/services/request_states.py` | `test_request_states.py` | Aprobado |
| Metadatos y deduplicación documental | `app/db/models/document.py` | modelos y migración | Unitario aprobado; PostgreSQL en CI |
| Idempotencia de mensajes | `app/db/models/whatsapp_message.py` | modelos y migración | Unitario aprobado; PostgreSQL en CI |
| Auditoría append-only | `app/db/models/audit_event.py` | `test_audit_events_reject_mutation` | Aprobado |
| Migración reversible | `alembic/versions/20260804_0001_initial_domain_model.py` | `test_upgrade_constraints_and_downgrade` | Requiere PostgreSQL CI |

Las pruebas usan exclusivamente datos sintéticos.
