# Resultado de Fase 11

## Umbrales de alerta

- Cola en cuarentena mayor a 50 documentos durante 10 minutos: crítica.
- Documento `scan_failed` con intentos agotados: crítica.
- Worker de escaneo sin ejecución durante 5 minutos: crítica.
- Worker de entrega sin ejecución durante 10 minutos: alta.
- Tasa de errores 5xx mayor al 2 % durante 5 minutos: alta.
- Latencia p95 del webhook mayor a 2 segundos durante 10 minutos: media.
- Firmas ClamAV con más de 24 horas: crítica.
- Cinco rechazos SSO del mismo sujeto en 10 minutos: alta.

## Preproducción

1. Configurar emisor, cliente, secreto, grupos y callback OIDC exacto.
2. Generar `ADMIN_SESSION_KEY` aleatoria y separar staging de producción.
3. Ejecutar migraciones `upgrade → downgrade → upgrade` contra PostgreSQL real.
4. Validar R2 privado, ClamAV actualizado, workers y alertas con fallos sintéticos.
5. Ejecutar prueba E2E con identidades viewer, operator y security_admin.
6. Confirmar redacción de query strings, cookies y encabezados en proxy y APM.
7. Aprobar privacidad, matriz de accesos, responsables y procedimiento de incidentes.

## Rollback

La Fase 11 no modifica el esquema de datos. El rollback restaura la imagen 0.10.0, pero el token compartido solo podrá habilitarse durante una contingencia autorizada y con rotación inmediata posterior. Los workers documentales continúan independientes del panel.
