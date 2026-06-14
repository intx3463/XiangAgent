"""动态工具构建器（自动持久化到 tools/custom/）"""
import os
import json
import time
from pathlib import Path
from .sandbox import safe_exec_tool
from .registry import TOOL_REGISTRY, register_tool

CUSTOM_TOOLS_DIR = Path(__file__).parent / "custom"
INDEX_FILE = CUSTOM_TOOLS_DIR / "_index.json"


def _ensure_custom_dir():
    """确保 custom 目录存在"""
    CUSTOM_TOOLS_DIR.mkdir(exist_ok=True)


def _load_index() -> dict:
    """加载工具索引"""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_index(index: dict):
    """保存工具索引"""
    _ensure_custom_dir()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def _save_tool_code(name: str, code: str, description: str):
    """保存工具代码到文件"""
    _ensure_custom_dir()
    tool_file = CUSTOM_TOOLS_DIR / f"{name}.py"
    with open(tool_file, "w", encoding="utf-8") as f:
        f.write(code)

    index = _load_index()
    index[name] = {
        "description": description,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file": f"{name}.py",
    }
    _save_index(index)


def build_tool(name: str, description: str, code: str, persist: bool = True):
    """从代码创建工具并注册"""
    if name in TOOL_REGISTRY:
        raise ValueError(f"工具 '{name}' 已存在")

    tool_func = safe_exec_tool(code, name)

    register_tool(name, tool_func)

    if persist:
        _save_tool_code(name, code, description)

    return tool_func


def load_custom_tools():
    """启动时加载所有自定义工具"""
    _ensure_custom_dir()
    index = _load_index()

    loaded = 0
    for name, meta in index.items():
        if name in TOOL_REGISTRY:
            continue

        tool_file = CUSTOM_TOOLS_DIR / meta["file"]
        if not tool_file.exists():
            continue

        try:
            code = tool_file.read_text(encoding="utf-8")
            build_tool(name, meta["description"], code, persist=False)
            loaded += 1
        except Exception as e:
            print(f"[tool_builder] 加载工具 '{name}' 失败: {e}")

    return loaded


def get_created_tools_count() -> int:
    """获取动态创建的工具数量"""
    return len([k for k in TOOL_REGISTRY if k not in ("internet_search", "weather", "hitokoto")])
