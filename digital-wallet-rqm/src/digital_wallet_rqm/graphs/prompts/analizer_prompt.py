from langchain_core.prompts import ChatPromptTemplate

_SYSTEM = """Clasifica el mensaje de un cliente de banca móvil en Bolivia.

tools = consultar un dato real de SU cuenta
  (solo disponible: su saldo)
retrieve = información general, igual para cualquier cliente
  (comisiones, tarifas, tasas, requisitos, plazos, cómo hacer un trámite,
   tarjetas de débito/crédito, transferencias ACH y QR, reclamos,
   derechos del consumidor financiero, seguridad y fraude)
analyst = saludo, agradecimiento, o pedir que aclares tu respuesta anterior

Reglas:
- Pregunta por un dato de SU cuenta (saldo) → tools
- Pregunta general (cómo, qué es, cuánto cuesta, cuándo, dónde) → retrieve
- Pide una acción que no podemos ejecutar (transferir, bloquear, pagar) → retrieve
  (se le explica cómo hacerlo)
- Mensaje corto de seguimiento ("¿y en dólares?", "esa") → misma ruta que el anterior
- Si hay duda → retrieve. Si menciona algo bancario → nunca analyst

Ejemplos:
"cuánto tengo en mi cuenta" → tools
"cuánto cuesta el mantenimiento de la tarjeta de crédito" → retrieve
"bloquea mi tarjeta" → retrieve
"cómo hago un reclamo al banco" → retrieve
"qué es la Defensoría del Consumidor Financiero" → retrieve
"¿y para la Platinum?" (antes: comisiones) → retrieve
"gracias" → analyst"""

ANALIZER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "Contexto previo: {context}\nMensaje: {question}"),
])
