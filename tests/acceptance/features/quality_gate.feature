# language: es
@acceptance
Característica: Quality Gate de Auto-Docs Torres
  Para impedir que una regresión llegue a producción
  Como responsable de calidad
  Quiero comprobar disponibilidad, autenticidad e idempotencia

  Antecedentes:
    Dado que la aplicación se ejecuta en un entorno aislado con datos sintéticos

  Escenario: La aplicación sólo declara disponibilidad cuando PostgreSQL responde
    Dado que PostgreSQL está disponible
    Cuando consulto el endpoint de disponibilidad
    Entonces la respuesta HTTP es 200
    Y la dependencia "database" aparece como "ok"

  Escenario: La aplicación falla de forma segura cuando PostgreSQL no responde
    Dado que PostgreSQL no está disponible
    Cuando consulto el endpoint de disponibilidad
    Entonces la respuesta HTTP es 503
    Y el estado de la aplicación es "unavailable"

  Escenario: Un webhook auténtico se procesa una sola vez
    Dado un webhook de Meta correctamente firmado
    Cuando envío el mismo webhook 2 veces
    Entonces el primer envío registra 1 mensaje aceptado
    Y el segundo envío registra 1 duplicado

  Escenario: Un webhook sin firma válida es rechazado
    Dado un webhook de Meta sin firma válida
    Cuando envío el webhook
    Entonces la respuesta HTTP es 401

  Escenario: El portal no expone documentos sin una sesión válida
    Dado que no tengo una sesión de portal
    Cuando consulto el portal del cliente
    Entonces la respuesta HTTP es 401

  Escenario: La landing dirige al número autorizado de WhatsApp
    Dado que el número público del bot es "525565808766"
    Cuando consulto la landing
    Entonces existe un vínculo a "https://wa.me/525565808766"
