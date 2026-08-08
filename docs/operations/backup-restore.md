# Respaldo y restauración

## Objetivos

- RPO objetivo: 60 minutos.
- RTO objetivo: 120 minutos.
- Retención mínima: 35 días.
- Una copia debe permanecer en una cuenta o ubicación separada del servicio primario.

## Respaldo

`python -m scripts.backup_database` ejecuta `pg_dump` en formato personalizado, cifra el
resultado con AES-256-GCM y genera un manifiesto SHA-256. La llave debe ser una cadena base64
URL-safe de 32 bytes y permanecer en el gestor de secretos, separada de PostgreSQL y del destino
de respaldo. El archivo temporal sin cifrar se crea con permisos restringidos y se elimina al
terminar.

Variables obligatorias: `DATABASE_URL`, `BACKUP_ENCRYPTION_KEY` y `BACKUP_OUTPUT_DIR`.

## Simulacro de restauración

La restauración solo acepta una base aislada mediante `RESTORE_DATABASE_URL` y requiere la frase
`RESTORE_CONFIRM=RESTORE_ISOLATED_DATABASE`. Después de `python -m scripts.restore_database`:

1. Ejecutar `alembic current` y verificar que coincide con `head`.
2. Comprobar conteos por tabla contra el manifiesto operativo del respaldo.
3. Ejecutar pruebas E2E con identidades y números sintéticos.
4. Medir tiempos y registrar RPO/RTO obtenidos.
5. Destruir de forma controlada la base del simulacro.

Nunca se debe restaurar sobre producción como prueba. El primer simulacro y uno trimestral son
condiciones de operación, no controles asumidos por este paquete.
