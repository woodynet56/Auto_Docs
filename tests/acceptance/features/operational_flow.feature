# language: es
Característica: Flujo operativo de clientes y gestores externos
  Como operación de Gestoría Reaver
  Quiero correlacionar cada solicitud y documento con su propietario
  Para evitar pérdidas, duplicados y entregas cruzadas

  Escenario: Un número no registrado se convierte en cliente aleatorio
    Dado un número de WhatsApp que no existe
    Cuando envía "Qué precio tiene una constancia este es NAVM12XXXX"
    Entonces se crea un cliente RANDOM
    Y se genera un folio REQ único sin validar rígidamente el RFC

  Escenario: Un cliente fijo no se duplica
    Dado un cliente FIXED registrado por teléfono
    Cuando envía una nueva solicitud
    Entonces se reutiliza el mismo cliente
    Y se conserva su tipo FIXED

  Escenario: La especialidad tiene prioridad sobre el horario
    Dado un gestor activo autorizado para constancia fiscal
    Y un gestor activo por horario
    Cuando se clasifica una constancia fiscal
    Entonces se asigna al gestor por tipo documental

  Escenario: El gestor responde citando el mensaje
    Dado una solicitud asignada con un mensaje saliente de Meta
    Cuando el gestor asignado cita ese mensaje y adjunta un PDF válido
    Entonces el documento se asocia al REQ correcto
    Y permanece en cuarentena hasta aprobar el análisis

  Escenario: El primer documento limpio completa la solicitud
    Dado un documento limpio asociado a una solicitud abierta
    Cuando el trabajador de entrega lo procesa
    Entonces Meta lo envía solamente al teléfono del cliente propietario
    Y la solicitud cambia a COMPLETED

  Escenario: Un segundo archivo no se entrega
    Dado una solicitud COMPLETED con una entrega registrada
    Cuando llega otro archivo para el mismo REQ
    Entonces el sistema lo rechaza
    Y registra el intento sin reenviarlo al cliente
