# Resultado de la Fase 10

La versión 0.10.0 incorpora una barrera antimalware obligatoria entre la recepción y la entrega.
Los archivos entran en cuarentena, se analizan mediante un worker idempotente y solo un resultado
limpio puede participar en una confirmación. Los fallos de infraestructura nunca se convierten en
aprobaciones implícitas.

También se incorpora una API administrativa operativa de exposición mínima para conteos, cola de
cuarentena y rechazo manual. No contiene contenido documental ni datos personales identificables.

La migración sobre PostgreSQL real permanece como control obligatorio del CI.
