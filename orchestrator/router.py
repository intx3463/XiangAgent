import json
import re
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

ROUTER_PROMPT = """你是一个任务路由器。分析用户的问题，判断是否需要调用多个子任务来回答。

可用工具:
{tool_descriptions}

用户问题: {query}

判断规则:
1. 如果问题简单、可以直接回答（如闲聊、简单计算、单个事实查询），选择 "direct"
2. 如果问题**只**涉及浏览器操作（打开网页、点击按钮、填写表单、滚动、截图等），选择 "direct"
   - 如果问题同时涉及浏览器操作和其他任务（如天气查询、名言获取），选择 "decompose"
3. 如果问题能直接使用某个本地工具完成（如天气查询用 weather 工具、名言获取用 hitokoto 工具），选择 "direct"
4. 只有用户明确要求使用浏览器操作时才走浏览器路径
5. 如果问题需要多方面信息、需要搜索、需要综合多个来源，选择 "decompose"
6. 如果用户要求创建新工具（如"创建一个计算器工具"、"写一个xxx工具"、"开发一个工具"），选择 "decompose"

请以 JSON 格式返回（不要包含 markdown 代码块标记）:
{{
    "decision": "direct 或 decompose",
    "reason": "判断理由"
}}

注意: 只返回 JSON，不要包含其他内容"""


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    return json.loads(text)


async def route(
    llm: BaseChatModel,
    query: str,
    tool_descriptions: str,
) -> dict:
    """主模型判断是否需要分解任务"""
    # 关键词回退检查：创建工具请求必须走 decompose
    create_keywords = ["创建工具", "创建一个", "写一个工具", "开发工具", "新建工具"]
    if any(kw in query for kw in create_keywords):
        return {"decision": "decompose", "reason": "检测到创建工具请求（关键词匹配）"}

    prompt = ROUTER_PROMPT.format(tool_descriptions=tool_descriptions, query=query)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return _parse_json_response(response.content)