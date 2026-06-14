"""FastAPI SSE 服务器 - 浏览器端流式显示（延迟加载优化）"""
import asyncio
import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

llm = None
graph = None
queue = None
_initialized = False


def _init_if_needed():
    """延迟初始化 - 第一次请求时才加载重依赖"""
    global llm, graph, queue, _initialized
    if _initialized:
        return
    from langchain.chat_models import init_chat_model
    from config import config
    from orchestrator.queue import TokenQueue
    from orchestrator.graph import build_graph
    from tools.registry import get_available_tool_descriptions

    llm = init_chat_model(config.get_model_string(), **config.get_model_kwargs())
    queue = TokenQueue()
    tool_desc = get_available_tool_descriptions()
    graph = build_graph(llm, tool_desc, queue)
    _initialized = True
    print("依赖加载完成")


@app.on_event("startup")
async def startup():
    print("服务器启动完成（依赖将在首次请求时加载）")


@app.on_event("shutdown")
async def shutdown():
    from tools.browser import browser_manager
    await browser_manager.stop()
    print("浏览器已关闭")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/tools")
async def get_tools():
    _init_if_needed()
    from tools.registry import get_available_tool_names
    return {"tools": get_available_tool_names()}


@app.get("/api/chat")
async def chat(query: str):
    _init_if_needed()

    async def event_generator():
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
                data = {
                    "task_id": event.task_id,
                    "type": event.token_type,
                    "content": event.content,
                    "metadata": event.metadata,
                    "timestamp": event.timestamp,
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.01)

        result = await task
        final = result.get("final_answer", "")
        yield f"data: {json.dumps({'type': 'final', 'content': final}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return EventStreamResponse(event_generator())


class EventStreamResponse(StreamingResponse):
    def __init__(self, content, **kwargs):
        super().__init__(content, media_type="text/event-stream", **kwargs)


app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
