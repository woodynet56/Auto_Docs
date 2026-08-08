# Punto de control — Fase 1

Fecha: 2026-08-04

## Implementado

- Estructura modular FastAPI.
- Configuración tipada y validación obligatoria de PostgreSQL.
- Motor SQLAlchemy asíncrono preparado para PostgreSQL.
- Health checks separados de vida y disponibilidad.
- Logging JSON con redacción de claves sensibles.
- Dependencias fijadas, pruebas, cobertura, lint, tipado y análisis de seguridad.
- GitHub Actions y Blueprint inicial de Render.
- ADR, documentación operativa y prueba de humo reproducible.

## No implementado

- Modelos, migraciones y máquina de estados (Fase 2).
- Landing pública (Fase 3).
- Webhook Meta, solicitudes, documentos, entrega y panel (Fases 4 a 8).
- Almacenamiento productivo o tratamiento de datos reales.

## Defectos encontrados y corregidos

1. Ruff inspeccionaba un directorio temporal de compilación: se excluyeron artefactos generados.
2. `pytest 8.4.2` tenía una vulnerabilidad conocida: se actualizó y fijó `pytest 9.0.3`.
3. La cobertura descendió a 84.93 % tras modernizar el cliente ASGI: se agregaron pruebas de
   ciclo de vida y endpoint raíz; resultado final 91.10 %.
4. El primer mock intentó modificar un atributo de solo lectura de SQLAlchemy: se reemplazó el
   motor completo por un doble controlado y la prueba aprobó.

## Riesgos y bloqueantes

- No se ejecutó integración contra una instancia PostgreSQL real en este entorno.
- Render requiere confirmar región, plan y cuenta antes de crear recursos con costo.
- Privacidad, almacenamiento privado, retención, Meta y cierre continúan bloqueando datos reales.

## Rollback

Esta fase es fundacional y no contiene migraciones ni datos. El rollback consiste en revertir el
commit de la versión `0.1.0`; no requiere restauración de base de datos.
