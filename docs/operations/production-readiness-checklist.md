# Checklist de liberación productiva

## Bloqueantes técnicos

- [ ] CI principal y certificación de preproducción en verde.
- [ ] Migración `upgrade → downgrade → upgrade` aprobada sobre copia aislada.
- [ ] E2E webhook → solicitud → documento limpio → confirmación → OTP → descarga auditada.
- [ ] Casos negativos de autorización horizontal, CSRF, replay, revocación e infección.
- [ ] k6 cumple error < 1 %, p95 < 500 ms y p99 < 1 s para el perfil definido.
- [ ] ZAP sin alertas altas/críticas y con medias resueltas o aceptadas con vencimiento.
- [ ] Restauración completa dentro de RPO 60 min / RTO 120 min.
- [ ] Alertas verificadas mediante fallos sintéticos de todas las dependencias.

## Bloqueantes organizacionales

- [ ] Aviso de privacidad y términos aprobados.
- [ ] Propietario y suplente para incidentes y continuidad.
- [ ] Matriz OIDC/RBAC aprobada con usuarios nominales.
- [ ] Runbook, escalamiento y rollback ensayados.
- [ ] Credenciales productivas rotadas y almacenadas en gestor de secretos.
- [ ] Decisión GO firmada por producto, operación, seguridad y responsable legal.

Una casilla sin evidencia equivale a **NO-GO**. Las excepciones requieren riesgo, responsable,
compensación y fecha de expiración por escrito.
