# Punto de control de Fase 2

## Implementado

- Tablas de usuarios, solicitudes, documentos, mensajes de WhatsApp y auditoría.
- Restricciones PostgreSQL para teléfono E.164, folio, unicidad, hashes y tamaños.
- Máquina de estados, estados terminales y concurrencia optimista.
- Migración Alembic reversible, servicio PostgreSQL 17.2 en CI y pre-deploy en Render.

## No implementado

- Rutas webhook, llamadas a Meta, cifrado de identificadores, almacenamiento, entrega y panel.

## Límite de validación

Las comprobaciones estáticas, unitarias, cobertura, seguridad y compilación se ejecutan localmente.
Este entorno no proporciona PostgreSQL ni permite descargar Alembic; por ello la prueba real de
upgrade/downgrade se omite localmente y es obligatoria en GitHub CI.

## Rollback

Antes de datos productivos: `alembic downgrade base`. Con datos productivos: respaldo verificado y
migración correctiva hacia adelante; no ejecutar un downgrade destructivo sin revisión.
