import os
import time
import random
from typing import Literal

from tavily import TavilyClient


def _get_client():
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise ValueError("TAVILY_API_KEY 环境变量未设置")
    return TavilyClient(api_key=api_key)


def _is_rate_limit_error(e: Exception) -> bool:
    """判断是否是限流错误"""
    msg = str(e).lower()
    return "429" in msg or "rate" in msg or "limit" in msg or "too many" in msg


def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
    max_retries: int = 2,
):
    """Run a web search using Tavily API with retry on rate limit.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
        topic: Search topic - "general", "news", or "finance"
        include_raw_content: Whether to include raw page content
        max_retries: Maximum retry attempts on rate limit
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            client = _get_client()
            return client.search(
                query,
                max_results=max_results,
                include_raw_content=include_raw_content,
                topic=topic,
            )
        except Exception as e:
            last_exception = e
            if _is_rate_limit_error(e) and attempt < max_retries:
                delay = min(2.0 * (2 ** attempt) + random.uniform(0, 1), 15.0)
                time.sleep(delay)
                continue
            raise

    raise last_exception
