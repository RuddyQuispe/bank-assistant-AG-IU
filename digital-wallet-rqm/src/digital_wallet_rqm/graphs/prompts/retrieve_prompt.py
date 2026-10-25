from langchain_core.prompts import ChatPromptTemplate

_SYSTEM = """Reescribe la pregunta del cliente como una consulta de búsqueda
autocontenida para documentos bancarios de Bolivia (tarifarios, reglamentos de ASFI,
guías de educación financiera).

Reglas:
- Usa el historial solo para completar lo que falta (producto, moneda, tipo de tarjeta).
- Conserva nombres de productos, montos y monedas (Bs, USD) tal como aparecen.
- No respondas la pregunta, no agregues datos nuevos.
- Devuelve solo la consulta, en una línea.

Ejemplos:
Historial: "Usuario: cuánto cuesta el mantenimiento de la tarjeta de crédito"
Pregunta: "¿y para la Platinum?"
Consulta: comisión de mantenimiento mensual tarjeta de crédito Platinum

Historial: "Usuario: cómo hago un reclamo al banco"
Pregunta: "¿y cuánto tardan en responder?"
Consulta: plazo de respuesta a un reclamo en el punto de reclamo de la entidad financiera"""

RETRIEVE_QUERY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", "Historial: {history}\nPregunta: {question}"),
])
