from langchain_core.messages import HumanMessage, SystemMessage, ToolCall
from langgraph.runtime import Runtime

from digital_wallet_rqm.config.settings import settings
from digital_wallet_rqm.core.llm_model import get_llm
from digital_wallet_rqm.graphs.context import GraphContext
from digital_wallet_rqm.graphs.prompts.tools_prompt import TOOLS_SYSTEM_PROMPT
from digital_wallet_rqm.graphs.state.bank_state import BankState, ToolResult, ToolsUpdate
from digital_wallet_rqm.graphs.tools import TOOLS
from digital_wallet_rqm.models.current_user import CurrentUser

_TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}


def _execute(tool_call: ToolCall, user: CurrentUser | None) -> ToolResult:
    tool = _TOOLS_BY_NAME.get(tool_call["name"])
    if tool is None:
        return ToolResult(tool=tool_call["name"], content="Error: herramienta no disponible.")

    # Las tools que declaran "user" lo reciben del servidor; se pisa cualquier valor que mande el LLM
    if "user" in tool.get_input_jsonschema().get("properties", {}):
        if user is None:
            return ToolResult(tool=tool_call["name"], content="Error: usuario no autenticado.")
        tool_call = {**tool_call, "args": {**tool_call["args"], "user": user}}

    # Invoking with the full ToolCall returns a ToolMessage
    message = tool.invoke(tool_call)
    return ToolResult(tool=tool_call["name"], content=message.text)


def node_tools(state: BankState, runtime: Runtime[GraphContext]) -> ToolsUpdate:
    """Elige las tools para la pregunta con el LLM y las ejecuta"""
    llm = get_llm(temperature=settings.LOW_TOMPERATURE).bind_tools(TOOLS)
    ai_message = llm.invoke([
        SystemMessage(content=TOOLS_SYSTEM_PROMPT),
        HumanMessage(content=state["question"]),
    ])
    if not ai_message.tool_calls:
        print("[tools]: el LLM no pidió ninguna tool")
        return {"tool_results": []}

    user = runtime.context.user
    tool_results = [_execute(tool_call, user) for tool_call in ai_message.tool_calls]
    for result in tool_results:
        print(f"[tools]: {result["tool"]} -> {result["content"]}")
    return {"tool_results": tool_results}
