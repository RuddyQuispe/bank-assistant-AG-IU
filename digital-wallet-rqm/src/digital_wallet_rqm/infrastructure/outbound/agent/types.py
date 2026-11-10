from typing import Literal, TypedDict

# Single source of truth for the graph routes, shared by the state and the LLM output schema
Route = Literal["retrieve", "tools", "analyst"]


class Source(TypedDict):
    file: str
    page: int | str
