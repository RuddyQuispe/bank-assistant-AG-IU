from langchain_core.tools import BaseTool

from digital_wallet_rqm.graphs.tools.account_tools import get_balance

# Every tool the tools node can call; bound to the LLM and executed by ToolNode
TOOLS: list[BaseTool] = [get_balance]
