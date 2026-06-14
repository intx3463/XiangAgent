import asyncio
from langchain.chat_models import init_chat_model
from config import config
from orchestrator.queue import TokenQueue, TokenEvent
from orchestrator.graph import build_graph
from tools.registry import get_available_tool_descriptions, get_available_tool_names


def format_event(event: TokenEvent) -> str:
    """格式化事件输出"""
    if event.token_type == "thinking":
        return f"  💭 {event.content}"
    elif event.token_type == "tool_call":
        tool_name = event.metadata.get("tool_name", "")
        tool_args = event.metadata.get("tool_args", {})
        args_str = f"({tool_args})" if tool_args else ""
        return f"  🔧 {event.content}{args_str}"
    elif event.token_type == "tool_result":
        return f"  📋 {event.content}"
    elif event.token_type == "status":
        return f"  {event.content}"
    elif event.token_type == "token":
        return event.content
    elif event.token_type == "done":
        if event.task_id != "main":
            return f"\n  ✅ 任务 {event.task_id} 完成"
        return ""
    elif event.token_type == "error":
        return f"\n  ❌ 任务 {event.task_id}: {event.content}"
    return ""


async def main():
    from tools.registry import TOOL_REGISTRY
    from tools.browser import browser_manager

    available = get_available_tool_names()
    unavailable = [n for n in TOOL_REGISTRY if n not in available]

    if unavailable:
        print("⚠️  以下工具不可用:")
        for name in unavailable:
            if name == "internet_search":
                print(f"   - {name}: TAVILY_API_KEY 未设置")
                print(f"     设置方法: 在 .env 文件中添加 TAVILY_API_KEY=your_key")
            else:
                print(f"   - {name}: 依赖缺失")
        print()

    queue = TokenQueue()
    llm = init_chat_model(config.get_model_string(), **config.get_model_kwargs())
    tool_desc = get_available_tool_descriptions()
    graph = build_graph(llm, tool_desc, queue)

    print(f"多智能体系统已启动！可用工具: {', '.join(available)}")
    print("输入 'quit' 退出。\n")

    try:
        while True:
            try:
                query = input("你: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break

            if query.lower() in ("quit", "exit", "q"):
                print("再见！")
                break
            if not query:
                continue

            print()
            task = asyncio.create_task(
                graph.ainvoke({
                    "messages": [{"role": "user", "content": query}],
                    "query": query,
                    "route": "",
                    "analysis": "",
                    "tasks": [],
                    "new_tools": [],
                    "created_tools": [],
                    "results": {},
                    "final_answer": "",
                    "shared_context": {},
                })
            )

            while not task.done():
                event = queue.get(timeout=0.05)
                if event:
                    output = format_event(event)
                    if output:
                        print(output, end="", flush=True if event.token_type == "token" else False)
                await asyncio.sleep(0.01)

            result = await task
            final = result.get("final_answer", "")
            if final:
                print(f"\n\n{'='*50}")
                print(f"最终回答:\n{final}")
                print(f"{'='*50}\n")
            else:
                print("\n  无结果\n")



if __name__ == "__main__":
    asyncio.run(main())
