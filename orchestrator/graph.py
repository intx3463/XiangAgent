import asyncio
import random
from langgraph.graph import StateGraph, END
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, AIMessageChunk, ToolMessage
from .state import OrchestratorState
from .router import route
from .decompose import decompose
from .subagent import run_subagents
from .synthesize import synthesize, format_results, has_valid_results
from .queue import TokenQueue, TokenEvent
from tools.builder import build_tool
from tools.registry import get_tools_by_names, get_available_tool_names

_api_semaphore = asyncio.Semaphore(1)


async def _run_with_retry(coro_factory, task_id: str, queue: TokenQueue, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            async with _api_semaphore:
                return await coro_factory()
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = ("429" in error_str or "rate" in error_str or
                           "limitation" in error_str or "too many requests" in error_str)
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = 2 ** (attempt + 1)
                queue.put(TokenEvent(task_id=task_id, token_type="status",
                    content=f"[{task_id}] API 限流，等待 {wait_time}s 后重试..."))
                await asyncio.sleep(wait_time)
            else:
                raise


def build_graph(llm: BaseChatModel, tool_descriptions: str, queue: TokenQueue):
    """构建 LangGraph 工作流"""

    async def route_node(state: OrchestratorState) -> dict:
        query = state.get("query") or state["messages"][-1].content
        queue.put(TokenEvent(task_id="main", token_type="thinking", content="正在分析问题类型..."))
        result = await route(llm, query, tool_descriptions)
        decision = result.get("decision", "direct")
        reason = result.get("reason", "")
        queue.put(TokenEvent(task_id="main", token_type="thinking", content=f"分析完成: {decision}"))
        queue.put(TokenEvent(task_id="main", token_type="status", content=f"判断: {decision} ({reason})"))
        return {"route": decision, "shared_context": {"route_reason": reason}}

    async def direct_node(state: OrchestratorState) -> dict:
        query = state.get("query") or state["messages"][-1].content
        queue.put(TokenEvent(task_id="main", token_type="status", content="处理中..."))

        import re
        browser_keywords = ["浏览器", "打开网页", "browser", "navigate", "点击", "填写", "截图", "滚动",
                           "哔哩哔哩", "bilibili", "每周必看", "观看", "视频", "播放"]
        has_browser_task = any(kw in query.lower() for kw in browser_keywords)

        tool_keywords = ["天气", "weather", "温度", "名言", "语录", "动漫", "hitokoto", "搜索", "search"]
        has_tool_task = any(kw in query.lower() for kw in tool_keywords)

        def filter_query_for_agent(agent_type: str) -> str:
            segments = re.split(r'[,，然后接着再]', query)
            browser_kw = ["浏览器", "打开网页", "browser", "navigate", "点击", "填写", "截图", "滚动",
                          "哔哩哔哩", "bilibili", "每周必看", "观看", "视频", "播放"]
            tool_kw = ["天气", "weather", "温度", "名言", "语录", "动漫", "hitokoto", "搜索", "search"]
            parts = []
            for seg in segments:
                seg = seg.strip()
                if not seg:
                    continue
                if agent_type == "browser" and any(kw in seg.lower() for kw in browser_kw):
                    parts.append(seg)
                elif agent_type == "tool" and any(kw in seg.lower() for kw in tool_kw):
                    parts.append(seg)
            return "、".join(parts) if parts else query

        async def run_browser_agent_task():
            from tools.browser_tools import BROWSER_TOOLS
            from deepagents import create_deep_agent

            queue.put(TokenEvent(task_id="browser", token_type="thinking", content="启动浏览器 agent..."))

            agent = create_deep_agent(
                model=llm,
                tools=BROWSER_TOOLS,
                system_prompt="""你是一个浏览器操作助手。只处理浏览器相关操作。

你的任务：
1. 打开网页、点击链接、浏览页面
2. 完成后输出简短的完成报告

不要处理天气、名言、搜索等工具查询，这些由其他 agent 处理。

新标签页处理：
1. B站等网站点击视频会在新标签页打开
2. 使用 browser_click_new_tab 点击会在新标签页打开的链接
3. 使用 browser_list_tabs 查看所有标签页
4. 使用 browser_switch_tab 切换到指定标签页

哔哩哔哩导航：
- 热门页面：https://www.bilibili.com/v/popular/all
- 每周必看：https://www.bilibili.com/v/popular/weekly
- 选择器：[href*="popular"], text=热门""",
            )

            browser_query = filter_query_for_agent("browser")
            full_response = ""
            async for event in agent.astream(
                {"messages": [{"role": "user", "content": browser_query}]},
            ):
                for node_name, node_output in event.items():
                    if not isinstance(node_output, dict):
                        continue
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessageChunk):
                            if msg.tool_calls:
                                for tc in msg.tool_calls:
                                    tool_name = tc.get("name", "unknown")
                                    tool_args = tc.get("args", {})
                                    queue.put(TokenEvent(
                                        task_id="browser", token_type="tool_call",
                                        content=f"[浏览器] 调用工具: {tool_name}",
                                        metadata={"tool_name": tool_name, "tool_args": tool_args}
                                    ))
                            if msg.content:
                                token = msg.content if isinstance(msg.content, str) else ""
                                if token.strip():
                                    full_response += token
                                    queue.put(TokenEvent(task_id="browser", token_type="token", content=token))
                        elif isinstance(msg, ToolMessage):
                            content = msg.content if isinstance(msg.content, str) else str(msg.content)
                            queue.put(TokenEvent(
                                task_id="browser", token_type="tool_result",
                                content=f"[浏览器] {content[:150]}",
                                metadata={"full_content": content}
                            ))

            if not full_response.strip():
                from tools.browser import browser_manager
                try:
                    await browser_manager.start()
                    title = await browser_manager.get_title()
                    url = await browser_manager.get_url()
                    full_response = f"浏览器操作完成。\n当前页面：{title}\nURL：{url}"
                except Exception:
                    full_response = "浏览器操作已完成"
            return full_response

        async def run_tool_agent_task():
            from tools.registry import weather_tool, hitokoto_tool, internet_search_tool
            from deepagents import create_deep_agent

            tool_list = [weather_tool, hitokoto_tool, internet_search_tool]
            queue.put(TokenEvent(task_id="tools", token_type="thinking", content="启动工具 agent..."))

            agent = create_deep_agent(
                model=llm,
                tools=tool_list,
                system_prompt="你是一个工具助手。根据用户问题使用合适的工具获取信息并简洁回答。",
            )

            tool_query = filter_query_for_agent("tool")
            full_response = ""
            async for event in agent.astream(
                {"messages": [{"role": "user", "content": tool_query}]},
            ):
                for node_name, node_output in event.items():
                    if not isinstance(node_output, dict):
                        continue
                    messages = node_output.get("messages", [])
                    for msg in messages:
                        if isinstance(msg, AIMessageChunk):
                            if msg.tool_calls:
                                for tc in msg.tool_calls:
                                    tool_name = tc.get("name", "unknown")
                                    queue.put(TokenEvent(
                                        task_id="tools", token_type="tool_call",
                                        content=f"[工具] 调用工具: {tool_name}",
                                        metadata={"tool_name": tool_name}
                                    ))
                            if msg.content:
                                token = msg.content if isinstance(msg.content, str) else ""
                                if token.strip():
                                    full_response += token
                                    queue.put(TokenEvent(task_id="tools", token_type="token", content=token))
                        elif isinstance(msg, ToolMessage):
                            content = msg.content if isinstance(msg.content, str) else str(msg.content)
                            full_response += f"\n{content}"
                            queue.put(TokenEvent(
                                task_id="tools", token_type="tool_result",
                                content=f"[工具] {content[:150]}",
                                metadata={"full_content": content}
                            ))
            return full_response.strip() or "工具执行完成"

        tasks_to_run = []
        if has_browser_task:
            tasks_to_run.append(run_browser_agent_task())
        if has_tool_task:
            tasks_to_run.append(run_tool_agent_task())

        if not tasks_to_run:
            from tools.registry import TOOL_REGISTRY, get_available_tool_descriptions
            tool_desc = get_available_tool_descriptions()
            match_prompt = f"可用工具:\n{tool_desc}\n\n用户问题: {query}\n\n如果有工具能直接满足需求，仅返回工具名。如果没有，仅返回 \"none\"。"
            match_resp = await llm.ainvoke([HumanMessage(content=match_prompt)])
            tool_name = match_resp.content.strip().strip('"').strip("'").strip("`")
            if tool_name in TOOL_REGISTRY:
                queue.put(TokenEvent(task_id="main", token_type="status", content=f"使用本地工具: {tool_name}"))
                tool_obj = TOOL_REGISTRY[tool_name]
                tool_result = tool_obj.invoke({})
                full_response = str(tool_result)
            else:
                create_keywords = ["创建工具", "创建一个", "写一个工具", "开发工具", "新建工具"]
                if any(kw in query for kw in create_keywords):
                    return {"route": "decompose", "shared_context": {"route_reason": "创建工具请求"}}
                full_response = ""
                async for chunk in llm.astream([HumanMessage(content=query)]):
                    if chunk.content:
                        token = chunk.content if isinstance(chunk.content, str) else ""
                        if token.strip():
                            full_response += token
                if not full_response.strip():
                    full_response = "无法生成回答，请重试。"
            queue.put(TokenEvent(task_id="main", token_type="done", content=""))
            return {"final_answer": full_response, "results": {"main": full_response}}

        if len(tasks_to_run) == 1:
            results_list = [await _run_with_retry(lambda: tasks_to_run[0], "browser", queue)]
        else:
            task_ids = ["browser", "tools"]
            wrapped = [_run_with_retry(lambda t=t: t, tid, queue)
                       for t, tid in zip(tasks_to_run, task_ids)]
            results_list = await asyncio.gather(*wrapped)

        if len(tasks_to_run) > 1:
            results_dict = {}
            if has_browser_task:
                results_dict["浏览器"] = results_list[0]
            if has_tool_task:
                idx = 1 if len(results_list) > 1 else 0
                results_dict["工具"] = results_list[idx]

            if has_valid_results(results_dict):
                queue.put(TokenEvent(task_id="main", token_type="thinking", content="正在综合所有结果..."))
                from .synthesize import SYNTHESIZE_PROMPT
                formatted = format_results(results_dict)
                prompt = SYNTHESIZE_PROMPT.format(query=query, results=formatted)
                full_response = ""
                async for chunk in llm.astream([HumanMessage(content=prompt)]):
                    if chunk.content:
                        token = chunk.content if isinstance(chunk.content, str) else ""
                        if token.strip():
                            full_response += token
                            queue.put(TokenEvent(task_id="main", token_type="token", content=token))
            else:
                combined = [v for v in results_dict.values() if v]
                full_response = "\n\n".join(combined) if combined else "执行完成"
        else:
            full_response = results_list[0] if results_list else "执行完成"

        queue.put(TokenEvent(task_id="main", token_type="done", content=""))
        return {"final_answer": full_response, "results": {"main": full_response}}

    async def decompose_node(state: OrchestratorState) -> dict:
        query = state.get("query") or state["messages"][-1].content
        
        has_browser = any(kw in query.lower() for kw in [
            "浏览器", "打开网页", "browser", "navigate", "点击", "填写", "截图", "滚动",
            "哔哩哔哩", "bilibili", "每周必看", "观看", "视频", "播放"
        ])
        
        if has_browser:
            queue.put(TokenEvent(task_id="main", token_type="thinking", content="检测到浏览器操作，切换到直接执行模式..."))
            return {"route": "direct", "shared_context": {"route_reason": "检测到浏览器操作"}}
        
        queue.put(TokenEvent(task_id="main", token_type="thinking", content="正在分析并分解任务..."))
        result = await decompose(llm, query, tool_descriptions)
        tasks = result.get("tasks", [])
        for t in tasks:
            t.setdefault("tools", [])
            t.setdefault("status", "pending")
        queue.put(TokenEvent(task_id="main", token_type="status", content=f"分解为 {len(tasks)} 个子任务"))
        for t in tasks:
            queue.put(TokenEvent(task_id="main", token_type="thinking", content=f"  {t['id']}: {t.get('description', t['query'])[:60]}"))
        return {
            "analysis": result.get("analysis", ""),
            "tasks": tasks,
            "new_tools": result.get("new_tools", []),
            "shared_context": {"analysis": result.get("analysis", ""), "task_count": len(tasks)}
        }

    async def tool_build_node(state: OrchestratorState) -> dict:
        new_tools = state.get("new_tools", [])
        if not new_tools:
            return {"created_tools": []}

        queue.put(TokenEvent(task_id="main", token_type="status", content=f"创建 {len(new_tools)} 个新工具..."))

        created = []
        errors = []
        for tool_def in new_tools:
            name = tool_def.get("name", "")
            desc = tool_def.get("description", "")
            code = tool_def.get("code", "")
            if not name or not code:
                errors.append(f"{name}: 缺少必要字段")
                continue

            try:
                build_tool(name, desc, code)
                created.append(name)
                queue.put(TokenEvent(task_id="main", token_type="status", content=f"  ✅ 工具 '{name}' 创建成功"))
            except Exception as e:
                errors.append(f"{name}: {e}")
                queue.put(TokenEvent(task_id="main", token_type="status", content=f"  ❌ 工具 '{name}' 创建失败: {e}"))

        return {"created_tools": created}

    async def execute_node(state: OrchestratorState) -> dict:
        tasks = state.get("tasks", [])
        if not tasks:
            return {"results": {}}

        queue.put(TokenEvent(task_id="main", token_type="thinking", content="开始并发执行子任务..."))

        shared_context = state.get("shared_context", {})
        results = await run_subagents(tasks, llm, queue, shared_context)
        return {"results": results, "shared_context": {**shared_context, "results": results}}

    async def synthesize_node(state: OrchestratorState) -> dict:
        query = state.get("query") or state["messages"][-1].content
        results = state.get("results", {})

        if not results:
            return {"final_answer": "没有收到任何子任务结果，请重试。"}

        if not has_valid_results(results):
            return {"final_answer": "所有子任务均未获取到有效信息。可能原因：网络问题或 API 配置错误。请检查配置后重试。"}

        queue.put(TokenEvent(task_id="main", token_type="thinking", content="正在综合所有结果..."))

        formatted = format_results(results)
        from .synthesize import SYNTHESIZE_PROMPT
        prompt = SYNTHESIZE_PROMPT.format(query=query, results=formatted)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                full_response = ""
                async for chunk in llm.astream([HumanMessage(content=prompt)]):
                    if chunk.content:
                        token = chunk.content if isinstance(chunk.content, str) else ""
                        if token.strip():
                            full_response += token
                            queue.put(TokenEvent(task_id="main", token_type="token", content=token))

                if not full_response.strip():
                    full_response = "综合结果生成失败，请重试。"

                queue.put(TokenEvent(task_id="main", token_type="done", content=""))
                return {"final_answer": full_response}
            except Exception as e:
                raise

        return {"final_answer": "综合结果失败，请重试。"}

    def should_decompose(state: OrchestratorState) -> str:
        return state.get("route", "direct")

    def after_decompose(state: OrchestratorState) -> str:
        route = state.get("route", "tool_build")
        if route == "direct":
            return "direct"
        return "tool_build"

    graph = StateGraph(OrchestratorState)

    graph.add_node("route", route_node)
    graph.add_node("direct", direct_node)
    graph.add_node("decompose", decompose_node)
    graph.add_node("tool_build", tool_build_node)
    graph.add_node("execute", execute_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("route")
    graph.add_conditional_edges(
        "route",
        should_decompose,
        {
            "direct": "direct",
            "decompose": "decompose",
        },
    )
    graph.add_conditional_edges(
        "decompose",
        after_decompose,
        {
            "direct": "direct",
            "tool_build": "tool_build",
        },
    )
    graph.add_edge("tool_build", "execute")
    graph.add_edge("execute", "synthesize")
    graph.add_edge("direct", END)
    graph.add_edge("synthesize", END)

    return graph.compile()
