import asyncio
import random
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage
from .queue import TokenQueue, TokenEvent
from tools.registry import get_tools_by_names
from tools.builder import load_custom_tools

SUBAGENT_PROMPT = """你是一个研究助手。针对以下任务进行搜索和分析。

任务描述: {description}

{context_section}

要求:
1. 使用提供的工具获取相关信息
2. 总结关键发现
3. 返回结构化的研究结果，包含要点总结"""


def _is_rate_limit_error(e: Exception) -> bool:
    """判断是否是限流错误"""
    error_str = str(e).lower()
    return ("429" in error_str or "rate" in error_str or "limitation" in error_str or
            "too many requests" in error_str)


async def run_subagent(
    task_id: str,
    query: str,
    description: str,
    assigned_tools: list[str],
    llm: BaseChatModel,
    queue: TokenQueue,
    shared_context: dict = None,
    max_retries: int = 2,
) -> str:
    """单个子 Agent 的执行逻辑，流式输出，支持退避重试"""

    load_custom_tools()  # 确保自定义工具已加载
    tools = get_tools_by_names(assigned_tools)

    context_section = ""
    if shared_context:
        if "analysis" in shared_context:
            context_section = f"整体分析: {shared_context['analysis']}"
        if "results" in shared_context:
            completed = [k for k, v in shared_context["results"].items() if v and not v.startswith("Error:")]
            if completed:
                context_section += f"\n已完成的任务: {', '.join(completed)}"

    for attempt in range(max_retries + 1):
        queue.put(TokenEvent(
            task_id=task_id,
            token_type="status",
            content=f"[{task_id}] 开始: {description[:60]}..."
        ))

        try:
            full_response = ""
            last_node_output = {}
            tool_call_list = []  # 按顺序存储工具名称

            if tools:
                from deepagents import create_deep_agent
                agent = create_deep_agent(
                    model=llm,
                    tools=tools,
                    system_prompt=SUBAGENT_PROMPT.format(description=description, context_section=context_section),
                )

                async for event in agent.astream(
                    {"messages": [{"role": "user", "content": query}]},
                ):
                    for node_name, node_output in event.items():
                        if node_output is not None:
                            last_node_output = node_output
                        if not isinstance(node_output, dict):
                            continue

                        messages = node_output.get("messages", [])
                        for msg in messages:
                            if isinstance(msg, (AIMessage, AIMessageChunk)):
                                if msg.tool_calls:
                                    for tc in msg.tool_calls:
                                        tool_name = tc.get("name", "")
                                        tool_args = tc.get("args", {})
                                        # 如果 tool_name 为空，使用工具调用的第一个参数值
                                        if not tool_name and tool_args:
                                            tool_name = next(iter(tool_args.values()), "未知操作")
                                        elif not tool_name:
                                            tool_name = "未知操作"
                                        tool_call_list.append(tool_name)
                                        queue.put(TokenEvent(
                                            task_id=task_id,
                                            token_type="tool_call",
                                            content=f"  [{task_id}] {tool_name}",
                                            metadata={"tool_name": tool_name, "tool_args": tool_args}
                                        ))
                                if msg.content:
                                    token = msg.content if isinstance(msg.content, str) else ""
                                    if token.strip():
                                        full_response += token
                                        queue.put(TokenEvent(
                                            task_id=task_id,
                                            token_type="token",
                                            content=token
                                        ))
                            elif isinstance(msg, ToolMessage):
                                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                                tool_name = tool_call_list.pop(0) if tool_call_list else "unknown"
                                queue.put(TokenEvent(
                                    task_id=task_id,
                                    token_type="tool_result",
                                    content=f"  [{task_id}] 工具返回: {content[:150]}",
                                    metadata={"tool_name": tool_name, "full_content": content}
                                ))

                if not full_response:
                    msgs = last_node_output.get("messages", [])
                    if msgs:
                        last = msgs[-1]
                        if hasattr(last, "content") and last.content:
                            full_response = last.content if isinstance(last.content, str) else ""
            else:
                queue.put(TokenEvent(
                    task_id=task_id, token_type="thinking",
                    content=f"  [{task_id}] 无工具，直接 LLM 分析..."
                ))
                prompt = f"任务: {description}\n\n请分析并回答以下查询: {query}"
                async for chunk in llm.astream([HumanMessage(content=prompt)]):
                    if chunk.content:
                        token = chunk.content if isinstance(chunk.content, str) else ""
                        if token.strip():
                            full_response += token
                            queue.put(TokenEvent(
                                task_id=task_id, token_type="token", content=token
                            ))

            if full_response.strip():
                queue.put(TokenEvent(task_id=task_id, token_type="done", content=""))
                return full_response

            if attempt < max_retries:
                queue.put(TokenEvent(
                    task_id=task_id, token_type="status",
                    content=f"[{task_id}] 结果为空，重试 ({attempt + 1}/{max_retries})..."
                ))
                continue

            return f"[{task_id}] 未获取到有效结果"

        except Exception as e:
            if attempt < max_retries:
                queue.put(TokenEvent(
                    task_id=task_id, token_type="status",
                    content=f"[{task_id}] 出错，重试 ({attempt + 1}/{max_retries})..."
                ))
                continue
            error_msg = f"Error: {e}"
            queue.put(TokenEvent(task_id=task_id, token_type="error", content=error_msg))
            return error_msg

    return f"[{task_id}] 所有重试均失败"


async def run_subagents(
    tasks: list[dict],
    llm: BaseChatModel,
    queue: TokenQueue,
    shared_context: dict = None,
) -> dict[str, str]:
    """并发执行所有子 Agent"""

    async def _run_task(task):
        return await run_subagent(
            task_id=task["id"],
            query=task["query"],
            description=task.get("description", task["query"]),
            assigned_tools=task.get("tools", []),
            llm=llm,
            queue=queue,
            shared_context=shared_context,
        )

    coros = [_run_task(t) for t in tasks]
    results = await asyncio.gather(*coros, return_exceptions=True)
    return {
        t["id"]: r if isinstance(r, str) else str(r)
        for t, r in zip(tasks, results)
    }
