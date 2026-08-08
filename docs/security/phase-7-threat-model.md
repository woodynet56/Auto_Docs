# Modelo de amenazas — Fase 7

| Riesgo | Control |
|---|---|
| Gestor ajeno confirma | Teléfono E.164, rol, actividad y asignación se verifican juntos |
| URL filtrada | Firma SigV4, vigencia de 60 a 900 segundos y bucket privado |
| Entrega duplicada | Restricción única por solicitud e ID de Meta único |
| Carrera entre workers | `FOR UPDATE SKIP LOCKED` y outbox persistente |
| Fallo de Meta | Reintento limitado, backoff y estado final explícito |
| Documento vencido | Consulta exige `expires_at` futuro y estado `ready` |
| Fuga en auditoría | Solo códigos de error; no URLs, claves, captions ni contenido |

La URL firmada es transferible durante su breve vigencia; el MVP no afirma que sea de un solo uso.
Antes de producción se recomienda añadir proxy autenticado o portal con sesión para revocación inmediata.
