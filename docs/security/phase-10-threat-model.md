# Modelo de amenazas — Fase 10

## Activos

- Documentos privados en R2.
- Estado y resultado del análisis.
- Token administrativo.
- Metadatos operativos y bitácora.

## Controles

- Cuarentena obligatoria antes de entrega o descarga.
- ClamAV `INSTREAM`: el escáner no recibe claves ni URLs de R2.
- Límite de tamaño aplicado antes y durante la recuperación.
- Reintentos limitados; el resultado indeterminado falla de forma cerrada.
- Exclusión de estados no limpios en confirmación y portal.
- Reclamación concurrente con `FOR UPDATE SKIP LOCKED`.
- API administrativa fuera de OpenAPI, autenticada y con salida sanitizada.
- Auditoría sin contenido, nombre original, hash, firma detectada ni clave de almacenamiento.

## Riesgo residual

Un motor basado en firmas no detecta todas las amenazas nuevas. Antes de producción deben
activarse actualizaciones automáticas de firmas, monitoreo de antigüedad de la base, aislamiento
de red del escáner y alertas cuando crezca la cola o se agoten reintentos. El token administrativo
es autenticación de servicio, no identidad individual; un panel humano completo requiere SSO,
roles y trazabilidad por usuario en una iteración posterior.
