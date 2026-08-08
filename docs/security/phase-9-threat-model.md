# Modelo de amenazas — Fase 9

## Activos

- Credencial opaca del portal, OTP, sesión autenticada y documentos privados.

## Controles

- Token de acceso de alta entropía almacenado solo como hash.
- OTP almacenado como HMAC ligado al token; nunca se registra en claro.
- Mensajes separados para enlace y código.
- Caducidad, intentos limitados, bloqueo temporal y revocación persistente.
- Rotación de la credencial al verificar para invalidar el enlace original.
- CSRF de doble envío, cookies seguras y política CSP restrictiva.

## Riesgo residual

Una persona con control completo del WhatsApp del cliente puede recibir ambos mensajes.
Para MFA independiente deberá añadirse un canal distinto o una identidad autenticada.
