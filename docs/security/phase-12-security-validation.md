# Validación de seguridad dinámica — Fase 12

El flujo CI ejecuta OWASP ZAP únicamente contra una URL HTTPS de preproducción proporcionada de
forma explícita. Nunca debe apuntarse a producción. Las alertas altas o críticas bloquean la
liberación; las medias requieren corrección o aceptación documentada con vencimiento.

Los escenarios mínimos manuales abarcan sesión OIDC alterada/expirada, CSRF, acceso horizontal a
documentos, repetición de webhook, reutilización de OTP, descarga revocada, archivo infectado y
agotamiento de límites. Las pruebas usan datos sintéticos y no conservan contenido descargado.
