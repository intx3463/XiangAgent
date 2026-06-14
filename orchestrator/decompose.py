import json
import re
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

DECOMPOSE_PROMPT = """你是一个任务分解专家。分析用户的问题，将其分解为多个独立的子任务。

可用工具:
{tool_descriptions}

用户问题: {query}

请以 JSON 格式返回（不要包含 markdown 代码块标记）:
{{
    "analysis": "对问题的分析",
    "tasks": [
        {{
            "id": "T1",
            "query": "子任务1的具体查询",
            "description": "子任务描述",
            "tools": ["工具名"]
        }}
    ],
    "new_tools": [
        {{
            "name": "工具名",
            "description": "工具描述",
            "code": "from langchain_core.tools import tool\\n\\n@tool\\ndef tool_name(param: str) -> str:\\n    \\"\\"\\"工具描述\\"\\"\\"\\n    # 工具实现\\n    return result"
        }}
    ]
}}

注意:
1. 每个子任务应该是独立的、可并行执行的
2. 根据子任务需求分配合适的工具，tools 数组中的工具名必须是上面列出的可用工具之一
3. 如果问题简单，可以只分解为 1-2 个子任务
4. 如果问题复杂，可以分解为 3-5 个子任务
5. 每个子任务的 query 应该是具体的、可搜索的查询
6. 如果现有工具无法满足某个子任务的需求，可以在 new_tools 字段中定义新工具
7. new_tools 中的代码必须使用 @tool 装饰器，必须有类型注解和文档字符串
8. 只在现有工具确实无法满足需求时才创建新工具
9. new_tools 可以为空数组，表示不需要创建新工具"""


def _parse_json_response(text: str) -> dict:
    """从 LLM 响应中提取 JSON"""
    text = text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    return json.loads(text)


async def decompose(llm: BaseChatModel, query: str, tool_descriptions: str) -> dict:
    """将用户查询分解为多个子任务，并分配工具"""
    prompt = DECOMPOSE_PROMPT.format(tool_descriptions=tool_descriptions, query=query)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    result = _parse_json_response(response.content)

    new_tools = result.get("new_tools", [])
    tasks = result.get("tasks", [])
    for t in tasks:
        t.setdefault("tools", [])
        t.setdefault("status", "pending")

    return {"analysis": result.get("analysis", ""), "tasks": tasks, "new_tools": new_tools}