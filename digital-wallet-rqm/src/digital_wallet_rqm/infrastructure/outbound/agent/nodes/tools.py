from uuid import uuid4

from langchain_core.callbacks import dispatch_custom_event
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolCall
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_config
from langgraph.runtime import Runtime
from pydantic import BaseModel

from digital_wallet_rqm.domain.models import AccountBalance
from digital_wallet_rqm.infrastructure.outbound.agent.context import GraphContext
from digital_wallet_rqm.infrastructure.outbound.agent.display_tools import (
    SHOW_ACCOUNT_BALANCE,
    balance_card_args,
    client_can_display,
    display_messages,
)
from digital_wallet_rqm.infrastructure.outbound.agent.nodes.interface import MANUALLY_EMIT_TOOL_CALL
from digital_wallet_rqm.infrastructure.outbound.agent.prompts.tools_prompt import TOOLS_SYSTEM_PROMPT
from digital_wallet_rqm.infrastructure.outbound.agent.state.bank_state import BankState, ToolResult, ToolsUpdate
from digital_wallet_rqm.infrastructure.outbound.agent.tools import TOOLS
from digital_wallet_rqm.infrastructure.outbound.llm.llm_model import get_llm
from digital_wallet_rqm.infrastructure.settings import settings

_TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def _execute(tool_call: ToolCall, context: GraphContext) -> tuple[ToolResult, object]:
    """Ejecuta la tool; devuelve su texto y sus datos (artifact) si la tool los trae"""
    tool = _TOOLS_BY_NAME.get(tool_call["name"])
    if tool is None:
        return ToolResult(tool=tool_call["name"], content="Error: herramienta no disponible."), None

    # Las tools que declaran "user" o "accounts" los reciben del servidor; se pisa lo que mande el LLM
    # Campos del modelo y no el JSON schema: "accounts" es un puerto y no tiene representación JSON
    schema = tool.get_input_schema()
    declared = schema.model_fields if issubclass(schema, BaseModel) else {}
    injected: dict[str, object] = {}
    if "user" in declared:
        if context.user is None:
            return ToolResult(tool=tool_call["name"], content="Error: usuario no autenticado."), None
        injected["user"] = context.user
    if "accounts" in declared:
        if context.accounts is None:
            return ToolResult(tool=tool_call["name"], content="Error: cuentas no disponibles."), None
        injected["accounts"] = context.accounts
    tool_call = {**tool_call, "args": {**tool_call["args"], **injected}}

    # Invoking with the full ToolCall returns a ToolMessage
    message = tool.invoke(tool_call)
    return ToolResult(tool=tool_call["name"], content=message.text), getattr(message, "artifact", None)


def _show_balance_card(
    result: ToolResult, account: AccountBalance, config: RunnableConfig
) -> tuple[ToolResult, list[AnyMessage]]:
    """Manda la tarjeta del saldo al navegador, la deja en el historial y da al interpreter un texto sin el monto"""
    # 1. Tool call de solo mostrar: AG-UI la convierte en TOOL_CALL_START/ARGS/END con los datos reales
    call_id = f"balance-{uuid4().hex}"
    args = balance_card_args(account)
    event = {"id": call_id, "name": SHOW_ACCOUNT_BALANCE, "args": args}
    dispatch_custom_event(MANUALLY_EMIT_TOOL_CALL, event, config=config)

    # 2. La misma tarjeta (mismo id) queda en el checkpoint: al volver a la sesión se vuelve a dibujar
    messages = display_messages(call_id, SHOW_ACCOUNT_BALANCE, args)

    # 3. El monto ya se ve en la tarjeta (que puede estar oculto): el texto no lo repite
    content = (
        f"Se mostró al cliente una tarjeta con el saldo de su {account.account_type} {account.masked_number}. "
        "El monto se ve en la tarjeta."
    )
    return ToolResult(tool=result["tool"], content=content), messages


def node_tools(state: BankState, runtime: Runtime[GraphContext]) -> ToolsUpdate:
    """Elige las tools para la pregunta con el LLM y las ejecuta"""
    # 1. El LLM elige qué tools usar
    llm = get_llm(temperature=settings.LOW_TOMPERATURE).bind_tools(TOOLS)
    ai_message = llm.invoke([
        SystemMessage(content=TOOLS_SYSTEM_PROMPT),
        HumanMessage(content=state["question"]),
    ])
    if not ai_message.tool_calls:
        print("[tools]: el LLM no pidió ninguna tool")
        return {"tool_results": []}

    # 2. Se ejecutan con el usuario del token y sus cuentas
    can_show_card = client_can_display(state, SHOW_ACCOUNT_BALANCE)
    tool_results: list[ToolResult] = []
    card_messages: list[AnyMessage] = []
    for tool_call in ai_message.tool_calls:
        result, data = _execute(tool_call, runtime.context)
        # 3. Si el cliente sabe dibujar la tarjeta, el saldo se muestra ahí
        if can_show_card and isinstance(data, AccountBalance):
            # get_config: la config del run actual (LangGraph no tipa nodos con runtime y config a la vez)
            result, messages = _show_balance_card(result, data, get_config())
            card_messages.extend(messages)
        print(f"[tools]: {result["tool"]} -> {result["content"]}")
        tool_results.append(result)
    if card_messages:
        return {"tool_results": tool_results, "messages": card_messages}
    return {"tool_results": tool_results}
