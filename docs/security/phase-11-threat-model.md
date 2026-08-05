# Modelo de amenazas — Fase 11

- **Suplantación:** el proveedor OIDC valida la identidad; el backend obtiene atributos desde `userinfo` mediante HTTPS.
- **CSRF y fijación:** estado firmado con nonce, cookie de estado corta, sesión nueva después del callback y token CSRF para mutaciones.
- **Escalada:** los grupos se traducen a una jerarquía cerrada. Sin grupo reconocido, el acceso se deniega.
- **Robo de sesión:** cookie cifrada `HttpOnly`, `Secure`, `SameSite=Strict`, limitada a `/admin` y con expiración máxima de ocho horas.
- **Divulgación:** el panel muestra solo metadatos mínimos; nunca documentos, identificadores, claves, OTP ni nombres originales.
- **Disponibilidad:** una caída del proveedor SSO impide nuevos accesos, pero no afecta webhooks, cuarentena ni workers.

Riesgo residual: la revocación de una sesión ya emitida depende de su TTL. Antes de producción se recomienda TTL de 60 minutos, revocación global mediante rotación de `ADMIN_SESSION_KEY` y cierre de sesión centralizado del proveedor.
