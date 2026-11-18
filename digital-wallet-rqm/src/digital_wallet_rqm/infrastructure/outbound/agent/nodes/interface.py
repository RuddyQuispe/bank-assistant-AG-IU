from uuid import uuid4

from langchain_core.callbacks import dispatch_custom_event
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from digital_wallet_rqm.infrastructure.outbound.agent.display_tools import DISPLAY_TOOLS
from digital_wallet_rqm.infrastructure.outbound.agent.prompts.interface_prompt import INTERFACE_SYSTEM_PROMPT
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import BankState, InterfaceUpdate
from digital_wallet_rqm.infrastructure.outbound.llm.llm_model import get_llm
from digital_wallet_rqm.infrastructure.settings import settings

# Evento que ag_ui_langgraph traduce a TOOL_CALL_START/ARGS/END (CustomEventNames.ManuallyEmitToolCall)
MANUALLY_EMIT_TOOL_CALL = "manually_emit_tool_call"
NO_CLIENT_TOOLS = "Desde aquí no puedo cambiar la apariencia; hazlo desde la app web."


def node_interface(state: BankState, config: RunnableConfig) -> InterfaceUpdate:
    """Pide al LLM la tool del cliente (tema, fuente) y la manda al navegador sin ejecutarla"""
    # 1. Sin tools del cliente (por ejemplo /chat) no hay nada que llamar.
    #    Las tools de solo mostrar (tarjetas) las emite el backend con datos reales: el LLM no las elige
    client_tools = [tool for tool in state.get("tools", []) if tool.get("name") not in DISPLAY_TOOLS]
    if not client_tools:
        print("[interface]: el cliente no mandó tools")
        message = AIMessage(content=NO_CLIENT_TOOLS)
        return {"response": message.text, "messages": [message]}

    # 2. El LLM elige la tool; solo conoce su descripción, el código vive en el navegador
    llm = get_llm(temperature=settings.LOW_TOMPERATURE).bind_tools(client_tools)
    message = llm.invoke([
        SystemMessage(content=INTERFACE_SYSTEM_PROMPT),
        HumanMessage(content=state["question"]),
    ])

    # 3. Emite cada tool call completa (TOOL_CALL_START/ARGS/END). Por streaming no sirve:
    #    Gemini manda nombre y args en un solo chunk y AG-UI descarta los args de ese primer chunk
    for call in message.tool_calls:
        # El navegador devuelve el resultado con este id: si el modelo no lo trae, se crea uno
        # y queda igual en el historial y en el evento
        call["id"] = call["id"] or f"call-{uuid4().hex}"
        event = {"id": call["id"], "name": call["name"], "args": call["args"]}
        dispatch_custom_event(MANUALLY_EMIT_TOOL_CALL, event, config=config)
    print(f"[interface]: tool calls={[call["name"] for call in message.tool_calls]}")
    return {"response": message.text, "messages": [message]}
