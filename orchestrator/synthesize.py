from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

SYNTHESIZE_PROMPT = """你是一个综合分析专家。请将以下多个研究结果综合成简洁的回答。

用户原始问题: {query}

各子任务的研究结果:
{results}

注意:
- 标记为 [失败] 或 [无结果] 的任务未能成功获取信息，请在回答中如实说明
- 只综合有实际内容的任务结果
- 如果所有任务都失败了，如实告知用户并建议重试

要求:
1. 回答要简洁，只输出最重要的信息
2. 不要重复问题，直接给出答案
3. 不要输出过程描述，只输出结果
4. 用中文回答
5. 不要使用 markdown 标题格式
6. 控制在 100 字以内"""


def format_results(results: dict[str, str]) -> str:
    """格式化结果，区分有效和无效"""
    valid_parts = []
    failed_tasks = []

    for task_id, result in results.items():
        if (result
                and not result.startswith("Error:")
                and not result.startswith("[")
                and "未获取到" not in result):
            valid_parts.append(f"### 任务 {task_id}\n{result}")
        else:
            failed_tasks.append(task_id)

    if failed_tasks:
        valid_parts.append(
            f"### 未完成的任务: {', '.join(failed_tasks)}\n"
            f"这些任务未能成功获取信息，请在回答中如实说明。"
        )

    return "\n\n".join(valid_parts) if valid_parts else "所有任务均未获取到有效结果。"


def has_valid_results(results: dict[str, str]) -> bool:
    """检查是否有有效结果"""
    for result in results.values():
        if (result
                and not result.startswith("Error:")
                and not result.startswith("[")
                and "未获取到" not in result):
            return True
    return False


async def synthesize(
    llm: BaseChatModel,
    query: str,
    results: dict[str, str],
) -> str:
    """综合所有子任务的结果"""
    if not results:
        return "没有收到任何子任务结果，请重试。"

    if not has_valid_results(results):
        return "所有子任务均未获取到有效信息。可能原因：网络问题或 API 配置错误。请检查配置后重试。"

    formatted = format_results(results)
    prompt = SYNTHESIZE_PROMPT.format(query=query, results=formatted)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return response.content
