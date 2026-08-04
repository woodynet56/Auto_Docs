# Fase 9 — Verificación reforzada del portal

| Requisito | Implementación | Evidencia |
|---|---|---|
| Código de un solo uso | HMAC-SHA256, seis dígitos, vigencia máxima de 10 minutos | `tests/unit/test_portal.py` |
| Separación de secretos | Enlace y código en mensajes distintos | `tests/unit/test_delivery.py` |
| Antifuerza bruta | Cinco intentos y bloqueo configurable de 15 minutos | `tests/unit/test_portal.py` |
| Sesión segura | Rotación después del OTP; cookie HttpOnly/Secure/Strict | `tests/api/test_portal.py` |
| CSRF | Token de doble envío y comparación constante | `tests/api/test_portal.py` |
| Navegador | CSP, no-store, no-referrer, DENY y nosniff | `app/api/portal.py` |
| Reversibilidad | Migración `20260804_0005` con downgrade | CI PostgreSQL |

El código enviado por WhatsApp refuerza la posesión del canal, pero no se declara MFA
independiente porque enlace y código utilizan el mismo medio.
