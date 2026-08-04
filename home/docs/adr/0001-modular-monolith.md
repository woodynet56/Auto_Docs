# ADR-0001: Monolito modular para el MVP

- Estado: aceptado para Fase 1
- Fecha: 2026-08-04

## Decisión

Usar un monolito modular FastAPI con capas separadas para API, dominio, servicios y persistencia.
PostgreSQL será la fuente transaccional. Meta WhatsApp y almacenamiento se implementarán mediante
adaptadores en fases posteriores.

## Razón

Reduce complejidad operativa inicial sin mezclar reglas de negocio con proveedores externos y
permite separar workers cuando el procesamiento de documentos lo requiera.

