# Procedimiento QA obligatorio — Auto-Docs Torres

## 1. Objetivo y política de liberación

Este procedimiento se ejecuta después de cada cambio. Ningún commit puede llegar a
producción si un control obligatorio falla, si falta evidencia o si existe una excepción sin
aprobación documentada. Las pruebas usan exclusivamente datos sintéticos y entornos aislados.

## 2. Quality Gates

| Gate | Momento | Controles | Criterio de salida |
|---|---|---|---|
| QG-1 Cambio local | Antes de commit | Ruff, formato, MyPy, Gherkin, regresión, cobertura, Bandit, dependencias, compilación | 100 % aprobado; cobertura >= 85 % |
| QG-2 Integración | Cada push/PR | QG-1 + PostgreSQL 17 + migraciones Alembic | Workflow verde y evidencia publicada |
| QG-3 Preproducción | Antes de liberar | E2E externo, ZAP, k6, resiliencia, respaldo/restauración | 0 críticos/altos; umbrales cumplidos |
| QG-4 Producción | Aprobación humana | Evidencias QG-1 a QG-3, rollback, accesos y privacidad | Dictamen GO firmado |

## 3. Ejecución después de cada cambio

1. Registrar el identificador del cambio, alcance, riesgo y criterios de aceptación.
2. Actualizar o agregar el escenario `.feature` que demuestra el comportamiento modificado.
3. Ejecutar desde la raíz:

   ```bash
   python scripts/quality_gate.py --profile local
   ```

4. Corregir el primer fallo y repetir el gate completo. No se aceptan ejecuciones parciales como
   evidencia final.
5. Subir el cambio mediante Pull Request. GitHub ejecutará el perfil CI con PostgreSQL 17.
6. Revisar `qa-results/gherkin.xml`, cobertura y logs. Aprobar el PR únicamente si todos los jobs
   están verdes.
7. Desplegar primero a preproducción y ejecutar `Preproduction certification` con su URL HTTPS.
8. Completar la lista de producción y emitir `GO` o `NO-GO`.

## 4. Cobertura funcional mínima

Los escenarios deben mantener, como mínimo:

- `health/live` y `health/ready`, incluyendo fallo cerrado sin PostgreSQL.
- Autenticidad, límite de tamaño e idempotencia del webhook Meta.
- Cliente FIXED/RANDOM, REQ único, clasificación y asignación automática.
- Primer archivo válido, cuarentena, ClamAV, entrega y cierre.
- Rechazo del segundo archivo y aislamiento estricto entre solicitudes/clientes.
- OTP, sesión, CSRF, descarga mediada y auditoría.
- OIDC, roles `viewer/operator/security_admin` y prohibiciones por rol.
- Cifrado, integridad, respaldo/restauración y migración reversible.
- Landing, número autorizado `525565808766` y configuración Render.

Si un cambio toca uno de estos flujos, debe añadirse un escenario positivo, uno negativo y uno de
seguridad o límite aplicable.

## 5. Datos, entornos y evidencia

- Nunca usar teléfonos, RFC, CURP, documentos, tokens o credenciales reales.
- Separar bases de pruebas, preproducción y producción.
- La restauración sólo se prueba sobre una base desechable validada por el script.
- Conservar por liberación: commit SHA, workflow, JUnit Gherkin, cobertura, ZAP, k6, resultado de
  migraciones, restauración y checklist firmado.
- No conservar payloads con datos personales ni secretos en logs o artefactos.

## 6. Clasificación y bloqueo

| Severidad | Ejemplo | Decisión |
|---|---|---|
| Crítica | fuga de documentos, bypass de firma/SSO, pérdida de datos | NO-GO inmediato |
| Alta | autorización incorrecta, migración destructiva, malware entregado | NO-GO |
| Media | función principal incorrecta sin fuga ni pérdida | Corregir antes de producción |
| Baja | defecto visual menor con alternativa segura | Puede diferirse con aprobación y ticket |

No se permite reducir cobertura, excluir código nuevo o desactivar reglas para hacer pasar el gate.
Una excepción exige riesgo, alcance, responsable, vencimiento, mitigación y aprobación explícita.

## 7. Criterios GO / NO-GO

`GO` requiere simultáneamente: todos los gates verdes, cero vulnerabilidades críticas/altas,
cobertura >= 85 %, migración reversible aprobada, E2E crítico aprobado, restauración dentro de
RPO/RTO, rollback ensayado y aprobación del responsable funcional y técnico. Cualquier ausencia
produce `NO-GO`.
