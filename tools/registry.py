from langchain_core.tools import tool
from tools.search import internet_search
import importlib.util
import os

_tools_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools.py")
_spec = importlib.util.spec_from_file_location("tools_module", _tools_path)
_tools_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools_module)
get_weather = _tools_module.get_weather
get_hitokoto = _tools_module.get_hitokoto


@tool
def internet_search_tool(
    query: str,
    max_results: int = 5,
    topic: str = "general",
) -> str:
    """Search the internet for information.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
        topic: Search topic - "general", "news", or "finance"
    """
    try:
        result = internet_search(
            query=query,
            max_results=max_results,
            topic=topic,
        )
        if not result or "results" not in result:
            return "No results found"
        formatted = []
        for r in result["results"]:
            title = r.get("title", "No title")
            url = r.get("url", "")
            content = r.get("content", "")[:200]
            formatted.append(f"**{title}**\n{url}\n{content}\n")
        return "\n".join(formatted)
    except Exception as e:
        return f"Search error: {e}"


@tool
def weather_tool(city: str) -> str:
    """查询指定城市的当前天气信息，包括温度、湿度、风速等。

    Args:
        city: 城市名称，如：北京、上海、Tokyo
    """
    return get_weather(city)


@tool
def hitokoto_tool() -> str:
    """获取一条随机名言、动漫台词、经典语录。当用户询问动漫名言、名人名言、经典台词时使用此工具。"""
    return get_hitokoto()


TOOL_REGISTRY: dict[str, object] = {
    "internet_search": internet_search_tool,
    "weather": weather_tool,
    "hitokoto": hitokoto_tool,
}


def get_available_tools() -> list[str]:
    return list(TOOL_REGISTRY.keys())


def get_tools_by_names(names: list[str]) -> list:
    return [TOOL_REGISTRY[n] for n in names if n in TOOL_REGISTRY]


def get_tool_descriptions() -> str:
    return "\n".join(
        f"- {name}: {getattr(tool, 'description', 'No description')}"
        for name, tool in TOOL_REGISTRY.items()
    )


def register_tool(name: str, tool_func):
    """动态注册新工具"""
    if name in TOOL_REGISTRY:
        raise ValueError(f"工具 '{name}' 已存在")
    TOOL_REGISTRY[name] = tool_func


def _register_browser_tools():
    """注册浏览器工具"""
    try:
        from .browser_tools import BROWSER_TOOLS
        for tool_func in BROWSER_TOOLS:
            name = tool_func.name
            if name not in TOOL_REGISTRY:
                TOOL_REGISTRY[name] = tool_func
    except ImportError:
        pass

_register_browser_tools()


def _check_tool_available(name: str) -> bool:
    """检查工具是否实际可用"""
    if name == "internet_search":
        return bool(os.environ.get("TAVILY_API_KEY"))
    if name.startswith("browser_"):
        try:
            import playwright
            return True
        except ImportError:
            return False
    return True


def get_available_tool_names() -> list[str]:
    """获取实际可用的工具名（检查依赖是否满足）"""
    return [name for name in TOOL_REGISTRY if _check_tool_available(name)]


def get_available_tool_descriptions() -> str:
    """获取实际可用工具的描述"""
    return "\n".join(
        f"- {name}: {getattr(tool, 'description', 'No description')}"
        for name, tool in TOOL_REGISTRY.items()
        if _check_tool_available(name)
    )