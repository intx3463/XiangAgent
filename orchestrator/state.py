from typing import TypedDict, Annotated
from langgraph.graph import add_messages


class TaskItem(TypedDict):
    id: str
    query: str
    description: str
    tools: list[str]
    status: str  # pending / running / done / failed


class NewToolItem(TypedDict):
    name: str
    description: str
    code: str


class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    route: str  # "direct" 或 "decompose"
    analysis: str
    tasks: list[TaskItem]
    new_tools: list[NewToolItem]
    created_tools: list[str]
    results: dict[str, str]
    final_answer: str
    shared_context: dict  # agent 之间共享的上下文
