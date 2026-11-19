from collections.abc import Sequence

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from digital_wallet_rqm.infrastructure.outbound.agent.display_tools import DISPLAY_TOOLS, SCAN_QR


def format_recent_context(messages: Sequence[BaseMessage], limit: int = 2) -> str:
    """Formatea los últimos mensajes como 'Usuario: ...' / 'IA: ...'; vacío si hay menos de `limit`"""
    if len(messages) < limit:
        return ""
    return "\n".join(
        f"{"Usuario" if message.type == "human" else "IA"}: {message.content}"
        for message in messages[-limit:]
        if message.content
    )


def is_client_tool_result(messages: Sequence[BaseMessage]) -> bool:
    """True si el run trae el resultado de una tool del navegador (el último mensaje es de tipo tool)"""
    # Las tarjetas que guarda bank_tools también terminan en un ToolMessage, pero no son una acción del navegador.
    # El escaneo de un QR tampoco: no se confirma, lo procesa el backend (nodo qr_payment)
    if not messages or not isinstance(messages[-1], ToolMessage) or messages[-1].name in DISPLAY_TOOLS:
        return False
    return scanned_qr(messages) is None


def scanned_qr(messages: Sequence[BaseMessage]) -> str | None:
    """Resultado de scan_qr si el run lo trae al final (el token del QR o "cancelled"); None si no"""
    names = _tool_call_names(messages)
    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            break
        if names.get(message.tool_call_id) == SCAN_QR:
            return message.text
    return None


def _tool_call_names(messages: Sequence[BaseMessage]) -> dict[str, str]:
    """Nombre de cada tool call por su id: el ToolMessage del navegador solo trae el id"""
    return {
        call["id"]: call["name"]
        for message in messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
        if call["id"]
    }


def format_client_tool_results(messages: Sequence[BaseMessage]) -> str:
    """Resultados de las tools del navegador al final del historial, como 'set_font: ok: Roboto'"""
    names = _tool_call_names(messages)
    trailing: list[ToolMessage] = []
    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            break
        trailing.insert(0, message)
    return "\n".join(f"{names.get(message.tool_call_id, 'tool')}: {message.text}" for message in trailing)


def is_visible_in_chat(message: BaseMessage) -> bool:
    """Mensajes que ve el usuario: los suyos y las respuestas con texto (no tool calls ni sus resultados)"""
    return message.type in ("human", "ai") and bool(message.text)
