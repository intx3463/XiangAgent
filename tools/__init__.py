from .search import internet_search
from .registry import TOOL_REGISTRY

__all__ = ["internet_search", "TOOL_REGISTRY"]


def _init_custom_tools():
    """初始化时加载自定义工具"""
    try:
        from .builder import load_custom_tools
        loaded = load_custom_tools()
        if loaded > 0:
            print(f"[tools] 加载了 {loaded} 个自定义工具")
    except Exception as e:
        print(f"[tools] 加载自定义工具失败: {e}")


_init_custom_tools()